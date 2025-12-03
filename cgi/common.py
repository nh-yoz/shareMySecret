import sys
import config, json, os, yaml, time, cgi
from cryptography.fernet import Fernet

msg_sent = False


def get_key() -> str:
    return Fernet.generate_key().decode()


def encrypt(message: str, key: str) -> str:
    return Fernet(key).encrypt(message.encode()).decode()


def decrypt(message: str, key: str) -> str:
    return Fernet(key.encode()).decrypt(message.encode()).decode()


def print_headers(methods = ['POST', 'OPTIONS']):
    print(f'Access-Control-Allow-Origin: {config.cors}')
    print(f'Access-Control-Allow-Methods: {",".join(methods)}]')
    print('Access-Control-Allow-Headers: Content-Type')
    print('Access-Control-Max-Age: 86400') # Cache for 1 day (86400 seconds)
    print('Vary: Origin')
    print('Cache-Control: no-store')


def respond_with_error(status: int, message: str):
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


def respond(status: int, payload: str = ''):
    statuses = {
        '200': 'OK',
        '201': 'Created',
        '204': 'No Content'
    }
    print('Status: ' + str(status) + ' ' + statuses[str(status)])
    print('')
    if payload:
        print(payload)


def validate_token(token: str) -> bool:
    if type(token) != str or len(token) != 53:
        respond_with_error(400, 'Invalid token')
        return False
    filename = token[0:10]
    key = token[10:] + '='
    fname = config.secret_files_path + '/' + filename
    # Check file exists
    if not os.path.exists(fname):
        respond_with_error(404, 'Secret message doesn\'t exist')
        return False
    # Load only beginning of file to check expiry and decyption key
    with open(fname, "r", encoding="utf-8") as f:
        first_lines = "".join([next(f) for _ in range(3)])
        # Parse only the first 3 lines
        data = yaml.safe_load(first_lines)
    # check validity limit
    if time.time() > data['expires']:
        os.remove(fname)
        respond_with_error(410, 'The secret message has expired')
        return False
    try:
        if decrypt(data['control'], key) != filename:
            respond_with_error(400, 'Invalid token')
            return False
    except:
        respond_with_error(400, 'Invalid token')
        return False
    return True

class Content:
    type=os.environ.get("CONTENT_TYPE", "").lower()
    length=int(os.environ.get("CONTENT_LENGTH", "0"))


class Request:
    method=os.environ.get("REQUEST_METHOD", "").upper()
    arguments = cgi.parse()
    content = Content()
    def body():
        return sys.stdin.read()

request = Request()
