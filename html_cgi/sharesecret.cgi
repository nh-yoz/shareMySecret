#!/usr/bin/python3
import re
import os, cgi, sys, json, random, string, datetime, traceback, time, subprocess, yaml
from cryptography.fernet import Fernet
import config


msg_sent = False

def encrypt(message: str, key: str) -> str:
    return Fernet(key).encrypt(message.encode()).decode()

def decrypt(message: str, key: str) -> str:
    return Fernet(key.encode()).decrypt(message.encode()).decode()


def validate_encrypt_body(data: dict):
    try:
        keys = ['message', 'file', 'max_views', 'expires_in_value', 'expires_in_unit']
        # Check if all keys are available
        if any((missing_key:=key) not in data for key in keys):
            raise Exception(f'Missing key: \'{missing_key}\'')
        if any((invalid_key:=key) not in keys for key in data):
            raise Exception(f'Invalid key: \'{invalid_key}\'')

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

        # Check expires_in_unit is 'd', 'h' or 'm'
        if type(data['expires_in_unit']) is not str:
            raise Exception('expires_in_unit: must be a string')
        if data['expires_in_unit'] not in ['d', 'h', 'm']:
            raise Exception('expires_in_unit: should be one of "d", "h", "m"')

        # Check if message is ok (string and length > 0)
        if type(data['message']) is not str:
            raise Exception('message: must be a string')
        if len(data['message']) == 0:
            raise Exception('message: should not be empty')
        if not re.fullmatch(r'^[A-Za-z0-9+/]*={0,2}$', data['message']):
            raise Exception('message: should be base64 encoded')

        # Check if file is ok
        d = data['file'] 
        if d is not None and not isinstance(d, dict):
            raise Exception('file: must be null or an object')
        if d is not None:
            keys = ['name', 'size', 'data']
            # Check if all keys are available and no extra keys
            if any((missing_key:=key) not in d for key in keys):
                raise Exception(f'Missing key in \'file\': \'{missing_key}\'')
            if any((invalid_key:=key) not in keys for key in d):
                raise Exception(f'Invalid key in \'file\': \'{invalid_key}\'')
            # Check types of file
            for t in [ ('name', str, 'a string'), ('size', int, 'an integer'), ('data', str, 'a string') ]:
                if type(d[t[0]]) is not t[1]:
                    raise Exception(f'file.{t[0]}: must be {t[2]}')
            if d['size'] < 1:
                raise Exception(f'file.size must be > 0')
            if len(d['data']) == 0:
                raise Exception('file.data: should not be empty')
            if not re.fullmatch(r'^[A-Za-z0-9+/]*={0,2}$', d['data']):
                raise Exception('file.data: should be base64 encoded')

        return True
    except Exception as err:
        respond_with_error(400, err)
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
    except Exception as err:
        respond_with_error(400, err)
        return False

def store_secret(data: dict):
    global msg_sent
    try:
        file_name = ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(10))
        key = Fernet.generate_key().decode()
        data['message'] = encrypt(data['message'], key)
        if data['file'] is not None:
            data['file']['data'] = encrypt(data['file']['data'], key)
        fname = 'secret/' + file_name
        # Define expiration date
        time_multiplyers = {
            'm': ('minutes', 60),
            'h': ('hours', 60 * 60),
            'd': ('days', 24 * 60 * 60)
        }
        # 'views' must be first key in file so it can be changed after each retrieval
        data = { 'views': 0, 'expires': time.time() + data['expires_in_value'] * time_multiplyers[data['expires_in_unit']][1], **data }
        at_command = f'echo "rm -f {os.getcwd()}/{fname}" | at now + {data["expires_in_value"]} {time_multiplyers[data["expires_in_unit"]][0]}'
        del data['expires_in_value']
        del data['expires_in_unit']
        f = open(fname, 'w')
        yaml.safe_dump(data, f, sort_keys=False, default_flow_style=False)
        f.close()
        subprocess.run(["/bin/bash", "-c", at_command])
        print('Status: 201 Created')
        print('')
        resdict = { 'token': file_name + key[:-1] }
        print(json.JSONEncoder().encode(resdict))
        msg_sent = True
    except Exception as err:
        print(traceback.format_exc(), file=sys.stderr)
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
    try:
        fname = 'secret/' + token[0:10]
        if not os.path.exists(fname):
            respond_with_error(404, 'Secret message doesn\'t exist')
        key = token[10:] + '='
        f = open(fname, 'r')
        data = yaml.safe_load(f.read())
        f.close()
        # check validity limit
        if time.time() > data['expires']:
            os.remove(fname)
            respond_with_error(410, 'The secret message has expired')
            return
        data['views'] += 1
        try:
            data['message'] = decrypt(data['message'], key)
            if data['file'] is not None:
                data['file']['data'] = decrypt(data['file']['data'], key)
        except Exception as err:
            respond_with_error(400, 'Invalid token')
            return
        if data['views'] >= data['max_views'] and data['max_views'] != 0:
            os.remove(fname)
        else:
            # Change the number of views : it is the first line in yaml-file
            subprocess.run(["/bin/bash", "-c", f'/usr/bin/sed -i \'1s/[0-9]\+/{data["views"]}/\' {fname}'])
        print('Status: 200 OK')
        print('')
        print(json.JSONEncoder().encode(data))
        msg_sent = True
    except Exception as err:
        print(traceback.format_exc(), file=sys.stderr)
        respond_with_error(500, 'Unknown error')



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
except Exception as err:
    print(traceback.format_exc(), file=sys.stderr)
    respond_with_error(500, 'Unknown error')
