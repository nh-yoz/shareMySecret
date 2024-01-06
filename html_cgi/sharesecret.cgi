#!/usr/bin/python3
import os, cgi, sys, json, random, string, datetime
from cryptography.fernet import Fernet

def encrypt(message: string, key: string) -> string:
   return Fernet(key).encrypt(message.encode()).decode()

def decrypt(message: string, key: string) -> string:
   return Fernet(key.encode()).decrypt(message.encode()).decode()

def validate(data: dict):
   try:
      keys = ['secret_message', 'max_views', 'expires_in_value', 'expires_in_unit']
      # Check if all keys are available
      for key in keys:
         if key not in data:
            raise Exception(key + ': missing')

      # Check if message is ok (string and length > 0)
      if type(data['secret_message']) is not str:
         raise Exception('secret_message: must be a string')
      if len(data['secret_message']) == 0:
         raise Exception('secret_message: should not be empty')

      # Check if limit_views is integer and >= 0
      if type(data['max_views']) is not int:
         raise Exception('max_views: must be an integer')
      if data['max_views'] < 0:
         raise Exception('max_views: must be equal or greater than 0')

      # Check if expires_in_value is acceptable (integer > 0)
      if type(data['expires_in_value']) is not int:
         raise Exception('expires_in_value: must be an integer')
      if data['expires_in_value'] <= 0:
         raise Exception('expires_in_value: must be greater than 0')

      # Check expires_in_unit is 'd', 'y' or 'm'
      if type(data['expires_in_unit']) is not str:
         raise Exception('expires_in_unit: must be a string')
      if data['expires_in_unit'] not in ['d', 'h', 'm']:
         raise Exception('expires_in_unit: should be one of "d", "h", "m"')
   except Exception as error:
      respond_with_error(400, error)
      exit()

def store_secret(data: dict):
   try:
      secret = ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(10))
      key = Fernet.generate_key().decode()
      encrypted = encrypt(data['secret_message'], key)
      fname = 'secret/' + secret
      # Define expiration date
      expires = datetime.datetime.now()
      atCommand = 'echo "rm -f ' + os.getcwd() + '/' + fname + '" | at now + ' + str(data['expires_in_value'])
      if data['expires_in_unit'] == 'd':
         expires = expires + datetime.timedelta(days = data['expires_in_value'])
         atCommand += ' days'
      elif data['expires_in_unit'] == 'h':
         expires = expires + datetime.timedelta(hours = data['expires_in_value'])
         atCommand += ' hours'
      else: # 'm'
         expires = expires + datetime.timedelta(minutes = data['expires_in_value'])
         atCommand += ' minutes'
      dataStore = {
         'views': 0,
         'max_views': data['max_views'],
         'expires': expires.isoformat(),
         'secret_message': encrypted
      }
      f = open(fname, 'w')
      json.dump(dataStore, f)
      f.close()
#      trash = subprocess.run(atCommand, shell = True)
      print('Status: 201 Created')
      print('')
      resdict = { 'status': 201, 'token': secret + key[:-1] }
      print(json.JSONEncoder().encode(resdict))

#      print(atCommand)
#      print(trash)
   except:
      respond_with_error(500, 'The secret message could not be saved')
   exit()

def validate_token(token: str) -> bool:
   if type(token) is not str:
      return False
   if len(token) < 15:
      return False
   return True

def retrieve_secret(token: str):
   fname = 'secret/' + token[0:10]
   if not os.path.exists(fname):
      respond_with_error(404, 'Secret message doesn\'t exists')
   key = token[10:] + '='
   f = open(fname, 'r')
   data = f.read()
   data = json.loads(data)
   f.close()
   # check validity limit
   dateLimit = datetime.datetime.fromisoformat(data['expires'])
   now = datetime.datetime.now()
   if now > dateLimit:
      os.remove(fname)
      respond_with_error(410, 'The secret message has expired')
   data['views'] += 1
   try:
      message = decrypt(data['secret_message'], key)
   except:
      respond_with_error(400, 'Invalid token')
   if data['views'] >= data['max_views'] and data['max_views'] != 0:
      os.remove(fname)
   else:
      f = open(fname, 'w')
      json.dump(data, f)
      f.close
   print('Status: 200 OK')
   print('')
   resdict = { 'status': 200, 'message': str(message), 'expires_at': dateLimit.isoformat(), 'views': data['views'], 'max_views': data['max_views'] }
   print(json.JSONEncoder().encode(resdict))
   exit()

def respond_with_error(status: int, message: str):
   errors = {
      '400': 'Bad Request',
      '401': 'Unauthorized',
      '404': 'Not Found',
      '410': 'Gone',
      '500': 'Internal Server Error'
   }
   print('Status: ' + str(status) + ' ' + errors[str(status)])
   print('')
   resdict = { 'status': status, 'message': str(message) }
   print(json.JSONEncoder().encode(resdict))
   exit()



##########################
# Main program
##########################

print('Content-type: application/json')
print('Access-Control-Allow-Origin: https://misc.niklashook.fr')
print('Vary: Origin')
print('Cache-Control: no-store')

arguments = cgi.parse() # Should return response as { 'method': post/get, 'token': string if method=post }
body = sys.stdin.read()
if 'method' not in arguments:
   respond_with_error(400, 'Request method parameter is missing')
if arguments['method'][0].lower() == 'post':
   try:
      data = json.loads(body)
   except:
      respond_with_error(400, 'Invalid body')
   validate(data)
   store_secret(data)
elif arguments['method'][0].lower() == 'get':
   if 'token' not in arguments:
      respond_with_error(400, 'Missing token parameter')
   if not validate_token(arguments['token'][0]):
      respond_with_error(400, 'Invalid token format')
   retrieve_secret(arguments['token'][0])
else:
   respond_with_error(400, 'Bad request method parameter')
