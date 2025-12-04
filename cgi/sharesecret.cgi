#!/usr/bin/python3
import os, sys, json, yaml, random, string, traceback, time
import config, common, validation
from common import request as req

def validate_encrypt_body(data: dict):
    test_dict = {
        'message': [ 'and', (('type', 'str'), 'base64')],
        'file': [ 'or', (('type', 'none'), ('type', 'dict')) ],
        'max_views': [ 'and', (('type', 'int'), ('minmax', '[0,999999999]'))],
        'expires_in_unit': [ 'oneof', ('m', 'h', 'd') ],
        'expires_in_value': [ 'and', (('type', 'int'), ('min', 0))]
    }
    try:
        validation.validate_dict(data, test_dict)
    except Exception as err:
        common.respond_with_error(400, err)
        return False
    try:
        # Check if expires in at most 30 days
        total_sec = { 'm': 60, 'h': 60 * 60, 'd': 24 * 60 * 60 }[data['expires_in_unit']] * data['expires_in_value']
        if total_sec > 30 * 24 * 60 * 60:
            raise Exception('expires: should be less than 30 days')

        # Further check if file is ok
        test_dict = {
            'name': [ 'and', (('type', 'str'), ('minmax', '[1,256]')) ],
            'size': [ 'and', (('type', 'int'), ('min', 1)) ],
            'data': [ 'and', (('type', 'str'), 'base64') ]
        }
        try:
            if data['file'] is not None:
                validation.validate_dict(data['file'], test_dict)
        except Exception as err:
            common.respond_with_error(400, err)
            return False
        return True
    except Exception as err:
        common.respond_with_error(400, err)
        return False


def validate_decrypt_body(data: dict) -> bool:
    test_dict = {
        'token': [ ('type', 'str' ), ('minmax', '[53,53]') ]
    }
    try:
        validation.validate_dict(data, test_dict)
    except Exception as err:
        common.respond_with_error(400, err)
        return False
    return common.validate_token(data['token'])


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
        # 'control' must be the third key in file for checking key
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


def increment_views(filename: str):
    with open(filename, "r+b") as f:
        # Read only the first line
        first_line_bytes = f.readline()
        first_line = first_line_bytes.decode("utf-8")
        # Parse first line as YAML
        data = yaml.safe_load(first_line)
        try:
            validation.validate_dict(data, { 'views': [ ('regex', '^[0-9]{9}$') ]})
        except Exception as err:
            raise err
        # Parse & increment the view counter
        old_value_str = data["views"]
        new_value_int = int(old_value_str) + 1
        data["views"] = f'{new_value_int:09d}' # always 9 digits
        # Dump back using yaml, **keeping it on one line**
        # default_flow_style=True → preserves inline `{key: value}`
        updated_line = yaml.safe_dump(data, default_flow_style=False)
        # PyYAML adds a newline; remove it to match original format
        updated_line = updated_line.rstrip("\n")

        # Ensure same length for in-place update
        if len(updated_line) != len(first_line):
            raise ValueError(
                "Updated line has different length; cannot update in place safely.\n"
                f"old: {len(first_line)}, new: {len(updated_line)}\n"
                f"old_line: {first_line!r}\nnew_line: {updated_line!r}"
            )
        # Rewrite only the first line
        f.seek(0)
        f.write(updated_line.encode("utf-8"))


def retrieve_secret(token: str):
    try:
        filename = token[0:10]
        fname = config.secret_files_path + '/' + filename
        key = token[10:] + '='
        # File and token is valid, go on...
        f = open(fname, 'r')
        data = yaml.safe_load(f.read())
        f.close()
        try:
            data['message'] = common.decrypt(data['message'], key)
            if data['file'] is not None:
                data['file']['data'] = common.decrypt(data['file']['data'], key)
        except Exception as err:
            common.respond_with_error(400, 'Invalid token')
            return
        data['views'] = int(data['views']) + 1
        del data['control']
        payload = json.JSONEncoder().encode(data)
        common.respond(200, payload)
        if data['max_views'] != 0 and data['views'] >= data['max_views']:
            os.remove(fname)
        else:
            # Change the number of views without resaving the file: it is the first line in yaml-file
            increment_views(fname)
            #subprocess.run(["/bin/bash", "-c", f'/usr/bin/sed -i \'1s/[0-9]\+/{data["views"]}/\' {fname}'])
    except Exception as err:
        print(traceback.format_exc(), file=sys.stderr)
        common.respond_with_error(500, 'Unknown error')



##########################
# Main program
##########################

try:
    common.print_headers(methods = ['POST', 'OPTIONS'])
    if req.method == 'OPTIONS':
        common.respond(204, '')
    elif req.method == 'POST':
        print('Content-type: application/json')
        if not validate_arguments(req.arguments, { 'allowed': ('action',), 'required': ('action',) }):
            exit()
        elif req.arguments['action'][0] not in ('encrypt', 'decrypt'):
            common.respond_with_error(400, 'Invalid action, must be \'encrypt\' or \'decrypt\'')
        elif req.content.type != 'application/json' or req.content.length == 0:
            common.respond_with_error(415, 'Json body required')
        elif req.content.length > config.max_secret_body_length:
            common.respond_with_error(413, f'Body must be less or equal to {config.max_secret_body_length} bytes')
        else:
            try:
                body = req.body()
                data = json.loads(body)
            except:
                common.respond_with_error(400, 'Invalid json body')
                exit()
            if req.arguments['action'][0] == 'encrypt' and validate_encrypt_body(data):
                store_secret(data)
            elif req.arguments['action'][0] == 'decrypt' and validate_decrypt_body(data):
                retrieve_secret(data['token'])
    else:
        common.respond_with_error(405, f"The method '{req.method}' is not allowed")
except Exception as err:
    print(traceback.format_exc(), file=sys.stderr)
    common.respond_with_error(500, 'Unknown error')
