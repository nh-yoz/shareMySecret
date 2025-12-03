#!/usr/bin/python3
import re
import os, cgi, sys, json, random, string, traceback, time, subprocess, yaml
import config, common
from common import request as req

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

        # Check if expires in at most 30 days
        total_sec = { 'm': 60, 'h': 60 * 60, 'd': 24 * 60 * 60 }[data['expires_in_unit']] * data['expires_in_value']
        if total_sec > 30 * 24 * 60 * 60:
            raise Exception('expires: should be less than 30 days')

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
        common.respond_with_error(400, err)
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
        common.respond_with_error(400, err)
        return False

def store_secret(data: dict):
    try:
        file_name = ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(10))
        key = common.get_key()
        data['control'] = common.encrypt(file_name, key)
        data['message'] = common.encrypt(data['message'], key)
        if data['file'] is not None:
            data['file']['data'] = common.encrypt(data['file']['data'], key)
        fname = config.secret_files_path + '/' + file_name
        # Define expiration date
        time_multiplyers = {
            'm': ('minutes', 60),
            'h': ('hours', 60 * 60),
            'd': ('days', 24 * 60 * 60)
        }
        # 'views' must be first key in file so it can be changed after each retrieval
        # 'expires' must be the second key in file for cleanup script
        data = { 'views': 0, 'expires': time.time() + data['expires_in_value'] * time_multiplyers[data['expires_in_unit']][1], **data }
        del data['expires_in_value']
        del data['expires_in_unit']
        f = open(fname, 'w')
        yaml.safe_dump(data, f, sort_keys=False, default_flow_style=False)
        f.close()
        resdict = { 'token': file_name + key[:-1] }
        payload = json.JSONEncoder().encode(resdict)
        common.respond(201, payload)
    except Exception as err:
        print(traceback.format_exc(), file=sys.stderr)
        common.respond_with_error(500, 'The secret message could not be saved')

def validate_token(token: str) -> bool:
    if type(token) is not str:
        return False
    if len(token) != 53:
        return False
    return True

def validate_arguments(given_args, valid_args):
    for key in given_args.keys():
        if not key in valid_args['allowed']:
            common.respond_with_error(400, f"Invalid parameter '{key}'")
            return False
        if len(given_args[key]) > 1:
            common.respond_with_error(400, f"Too many values for parameter '{key}'")
            return False
    for key in valid_args['required']:
        if not key in given_args.keys():
            common.respond_with_error(400, f"Missing required parameter '{key}'")
            return False
    return True


def retrieve_secret(token: str):
    try:
        if not common.validate_token():
            return
        filename = token[0:10]
        fname = config.secret_files_path + '/' + filename
        key = token[10:] + '='
        # File and token is valid, go on...
        f = open(fname, 'r')
        data = yaml.safe_load(f.read())
        f.close()
        data['views'] += 1
        try:
            data['message'] = common.decrypt(data['message'], key)
            if data['file'] is not None:
                data['file']['data'] = common.decrypt(data['file']['data'], key)
        except Exception as err:
            common.respond_with_error(400, 'Invalid token')
            return
        if data['views'] >= data['max_views'] and data['max_views'] != 0:
            os.remove(fname)
        else:
            # Change the number of views without resaving the file: it is the first line in yaml-file
            subprocess.run(["/bin/bash", "-c", f'/usr/bin/sed -i \'1s/[0-9]\+/{data["views"]}/\' {fname}'])
        payload = json.JSONEncoder().encode(data)
        common.respond(200, payload)
    except Exception as err:
        print(traceback.format_exc(), file=sys.stderr)
        common.respond_with_error(500, 'Unknown error')





##########################
# Main program
##########################

try:
    method=os.environ.get("REQUEST_METHOD", "").upper()
    cont_type=os.environ.get("CONTENT_TYPE", "").lower()
    cont_len=int(os.environ.get("CONTENT_LENGTH", "0"))
    arguments = cgi.parse() # Should return response as { 'action': encrypt/decrypt  }
    common.print_headers(methods = ['POST', 'OPTIONS'])
    if method != 'OPTIONS':
        print('Content-type: application/json')
    if method == 'OPTIONS':
        print('')
    elif method == 'POST':
        print('Accept: application/json')
        if not validate_arguments(arguments, { 'allowed': ('action',), 'required': ('action',) }):
            common.respond_with_error(405, f"The method '{method}' is not allowed")
        elif arguments['action'][0] not in ('encrypt', 'decrypt'):
            common.respond_with_error(400, 'Invalid action, must be \'encrypt\' or \'decrypt\'')
        elif cont_type != 'application/json' or cont_len == 0:
            common.respond_with_error(415, 'Json body required')
        elif cont_len > config.max_secret_body_length:
            common.respond_with_error(413, f'Body must be less or equal to {config.max_secret_body_length} bytes')
        else:
            try:
                body = sys.stdin.read()
                data = json.loads(body)
                if arguments['action'][0] == 'encrypt' and validate_encrypt_body(data):
                    store_secret(data)
                elif arguments['action'][0] == 'decrypt' and validate_decrypt_body(data):
                    retrieve_secret(data['token'])
            except:
                common.respond_with_error(400, 'Invalid json body')
except Exception as err:
    print(traceback.format_exc(), file=sys.stderr)
    common.respond_with_error(500, 'Unknown error')
