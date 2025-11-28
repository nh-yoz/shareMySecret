#!/usr/bin/python3
import os, cgi, sys, json, random, string, datetime, traceback
from cryptography.fernet import Fernet
import config


msg_sent = False

def encrypt(message: string, key: string) -> string:
    return Fernet(key).encrypt(message.encode()).decode()

def decrypt(message: string, key: string) -> string:
    return Fernet(key.encode()).decrypt(message.encode()).decode()


def validate_encrypt_body(data: dict):
    try:
        keys = ['secret_message', 'max_views', 'expires_in_value', 'expires_in_unit']
        # Check if all keys are available
        if any((missing_key:=key) not in data for key in keys):
            raise Exception(f'Missing key: \'{missing_key}\'')
        if any((invalid_key:=key) not in keys for key in data):
            raise Exception(f'Invalid key: \'{invalid_key}\'')

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
        return True
    except Exception as error:
        respond_with_error(400, error)
        return False


def validate_decrypt_body(data: dict):
    try:
        keys = ['token']
        # Check if all keys are available
        if any((missing_key:=key) not in data for key in keys):
            raise Exception(f'Missing key: \'{missing_key}\'')
        if any((invalid_key:=key) not in keys for key in data):
            raise Exception(f'Invalid key: \'{invalid_key}\'')
        if not validate_token(data['token']):
            raise Exception('Invalid value for \'token\'')
        return True
    except Exception as error:
        respond_with_error(400, error)
        return False

def store_secret(data: dict):
    global msg_sent
    try:
        secret = ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(10))
        key = Fernet.generate_key().decode()
        encrypted = encrypt(data['secret_message'], key)
        fname = 'secret/' + secret
        # Define expiration date
        expires = datetime.datetime.now()
        at_command = 'echo "rm -f ' + os.getcwd() + '/' + fname + '" | at now + ' + str(data['expires_in_value'])
        if data['expires_in_unit'] == 'd':
            expires = expires + datetime.timedelta(days = data['expires_in_value'])
            at_command += ' days'
        elif data['expires_in_unit'] == 'h':
            expires = expires + datetime.timedelta(hours = data['expires_in_value'])
            at_command += ' hours'
        else: # 'm'
            expires = expires + datetime.timedelta(minutes = data['expires_in_value'])
            at_command += ' minutes'
        data_store = {
            'views': 0,
            'max_views': data['max_views'],
            'expires': expires.isoformat(),
            'secret_message': encrypted
        }
        f = open(fname, 'w')
        json.dump(data_store, f)
        f.close()
        print('Status: 201 Created')
        print('')
        resdict = { 'status': 201, 'token': secret + key[:-1] }
        print(json.JSONEncoder().encode(resdict))
        msg_sent = True
    except:
        respond_with_error(500, 'The secret message could not be saved')

def validate_token(token: str) -> bool:
    if type(token) is not str:
        return False
    if len(token) < 15:
        return False
    return True

def validate_arguments(given_args, valid_args):
    for key in given_args.keys():
        if not key in valid_args['allowed']:
            respond_with_error(400, f"Invalid parameter '{key}'")
            return False
        if len(given_args[key]) > 1:
            respond_with_error(400, f"Too many values for parameter '{key}'")
            return False
    for key in valid_args['required']:
        if not key in given_args.keys():
            respond_with_error(400, f"Missing required parameter '{key}'")
            return False
    return True

def retrieve_secret(token: str):
    global msg_sent
    fname = 'secret/' + token[0:10]
    if not os.path.exists(fname):
        respond_with_error(404, 'Secret message doesn\'t exists')
    key = token[10:] + '='
    f = open(fname, 'r')
    data = f.read()
    data = json.loads(data)
    f.close()
    # check validity limit
    date_limit = datetime.datetime.fromisoformat(data['expires'])
    now = datetime.datetime.now()
    if now > date_limit:
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
    resdict = { 'status': 200, 'message': str(message), 'expires_at': date_limit.isoformat(), 'views': data['views'], 'max_views': data['max_views'] }
    print(json.JSONEncoder().encode(resdict))
    msg_sent = True

def respond_with_error(status: int, message: str):
    global msg_sent
    errors = {
        '400': 'Bad Request',
        '401': 'Unauthorized',
        '404': 'Not Found',
        '405': 'Method Not Allowed',
        '410': 'Gone',
        '413': 'Payload Too Large',
        '415': 'Unsupported Media Type',
        '500': 'Internal Server Error'
    }
    print('Status: ' + str(status) + ' ' + errors[str(status)])
    print('')
    resdict = { 'status': status, 'message': str(message) }
    print(json.JSONEncoder().encode(resdict))
    msg_sent = True



##########################
# Main program
##########################

try:
    print(f'Access-Control-Allow-Origin: {config.cors}')
    print('Access-Control-Allow-Methods: GET, POST, OPTIONS')
    print('Access-Control-Allow-Headers: Content-Type')
    print('Access-Control-Max-Age: 86400') # Cache for 1 day (86400 seconds)
    print('Vary: Origin')
    print('Cache-Control: no-store')
    method=os.environ.get("REQUEST_METHOD", "").upper()
    cont_type=os.environ.get("CONTENT_TYPE", "").lower()
    cont_len=int(os.environ.get("CONTENT_LENGTH", "0"))
    arguments = cgi.parse() # Should return response as { 'action': encrypt/decrypt  }
    if method != 'OPTIONS':
        print('Content-type: application/json')
    if method == 'OPTIONS':
        print('')
    elif method == 'POST':
        print('Accept: application/json')
        if not validate_arguments(arguments, { 'allowed': ('action',), 'required': ('action',) }):
            respond_with_error(405, f"The method '{method}' is not allowed")
        elif arguments['action'][0] not in ('encrypt', 'decrypt'):
            respond_with_error(400, 'Invalid action, must be \'encrypt\' or \'decrypt\'')
        elif cont_type != 'application/json' or cont_len == 0:
            respond_with_error(415, 'Json body required')
        elif cont_len > config.max_secret_body_length:
            respond_with_error(413, f'Body must be less or equal to {config.max_secret_body_length} bytes')
        else:
            try:
                body = sys.stdin.read()
                data = json.loads(body)
                if arguments['action'][0] == 'encrypt' and validate_encrypt_body(data):
                    store_secret(data)
                elif arguments['action'][0] == 'decrypt' and validate_decrypt_body(data):
                    retrieve_secret(data['token'])
            except:
                respond_with_error(400, 'Invalid json body')
except:
    print('')
    print(traceback.format_exc(), file=sys.stderr)
    respond_with_error(500, 'Unknown error')
