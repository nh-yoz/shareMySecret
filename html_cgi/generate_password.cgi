#!/usr/bin/python3
import random, string, math, sys, cgi, json

def generate_password(length: int, upper: int, lower: int, digits: int, specials: int) -> str:
    count_arr = [upper, lower, digits, specials]
    chars_arr = [string.ascii_uppercase, string.ascii_lowercase, string.digits, '!"#$%&\'()*+,-./:;<=>?@[\]^_{|}~']
    if length <= 0 or sum(count_arr) == 0:
        return ''
    chars = ''.join(chars_arr[i] if count_arr[i] > 0 else '' for i in range(len(count_arr)))
    pwd_found = False
    pwd = ''
    while not pwd_found:
        pwd_found = True
        pwd = ''.join(random.SystemRandom().choice(chars) for _ in range(length))
        for i in range(len(count_arr)):
            if sum(char in chars_arr[i] for char in pwd) < count_arr[i]:
                pwd_found = False
                break
    return pwd


def pwd_bits(pwd: str) -> int:
    chars_arr = [string.ascii_uppercase, string.ascii_lowercase, string.digits, '!"#$%&\'()*+,-./:;<=>?@[\]^_{|}~']
    nb = 0
    for arr in chars_arr:
        if any(c in arr for c in pwd):
            nb += len(arr)
    return round(math.log2(pow(nb, len(pwd))))


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


def validate(arguments):
    args = {}
    for param in ['length', 'upper', 'lower', 'digits', 'specials']:
        if param in arguments: 
            if len(arguments[param]) == 0:
                args[param] = 1
            elif len(arguments[param]) > 1:
                respond_with_error(400, f'Multiple values for parameter "{param}"')
            else:
                try:
                    args[param] = int(arguments[param][0])
                except:
                    respond_with_error(400, 'Values must be integers')
        else:
            respond_with_error(400, f'Request parameter "{param}" is missing')
    count = sum(args[key] for key in ['upper', 'lower', 'digits', 'specials'])
    if count == 0:
        respond_with_error(400, f'At least one required char type is required')
    elif count > args['length']:
        respond_with_error(400, f'Total required chars exceeds length')
    return args


##########################
# Main program
##########################

print('Content-type: application/json')
print('Access-Control-Allow-Origin: https://misc.niklashook.fr')
print('Vary: Origin')
print('Cache-Control: no-store')
arguments = cgi.parse() # Should return response as { 'method': post/get, 'token': string if method=post }
body = sys.stdin.read()
args = validate(arguments)
pwd = generate_password(args['length'], args['upper'], args['lower'], args['digits'], args['specials'])
if pwd == '':
   respond_with_error(500, 'No password could be generated for given options')
else: 
    print('Status: 200')
    print('')
    print(json.JSONEncoder().encode({ 'password': pwd, 'bits': pwd_bits(pwd)}))
