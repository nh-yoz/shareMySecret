#!/usr/bin/python3
import smtplib, json, traceback, sys, re, base64, cgi, os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import config

email_regex = re.compile(r'([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+')
msg_sent = False

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

def is_valid_email(email: str) -> bool:
    return re.fullmatch(email_regex, email)

def is_string(value) -> bool:
    return type(value) == str

def is_base64(value) -> bool:
    try:
        return base64.b64encode(base64.b64decode(value)).decode('utf-8') == value
    except Exception:
        return False

def is_string_array(value) -> bool:
    if not isinstance(value, list):
        return False
    for v in value:
        if not is_string(v):
            return False
    return True

def validate_body(obj):
    test_dict = {
        'to': ['an array of email addresses (strings)', is_string_array],
        'subject': ['a string', is_string],
        'text_message': ['a string', is_string],
        'html_message': ['a string', is_string]
    }
    for key in test_dict:
        if key not in obj:
            respond_with_error(400, f'Body is missing property "{key}"')
            return False
        elif not test_dict[key][1](obj[key]):
            respond_with_error(400, f'The property "{key}" should be {test_dict[key][0]}')
            return False
    if not is_base64(obj['html_message']):
        respond_with_error(400, f'The property "{key}" should be base64 encoded')
        return False
    if is_base64(obj['html_message']):
        obj['html_message'] = base64.b64decode(obj['html_message']).decode('utf-8')
    for email_address in obj['to']:
        if not is_valid_email(email_address):
            respond_with_error(400, f'{email_address} is not a valid email address')
            return False
    return True

def send_mail(obj):
    #msg = EmailMessage()
    msg = MIMEMultipart("alternative")
    msg['From'] = config.smtp_from
    msg['To'] = ", ".join(obj['to'])
    msg['Subject'] = obj['subject']
    msg.attach(MIMEText(obj['text_message'], 'plain'))
    msg.attach(MIMEText(obj['html_message'], 'html'))
    server = smtplib.SMTP_SSL(config.smtp_host, config.smtp_port) if config.smtp_ssl else smtplib.SMTP(config.smtp_host, config.smtp_port)
    if config.smtp_auth:
        server.login(config.smtp_username, config.smtp_password)
    server.send_message(msg)



##########################
# Main program
##########################

try:
    print(f'Access-Control-Allow-Origin: {config.cors}')
    print('Access-Control-Allow-Methods: POST, OPTIONS')
    print('Access-Control-Allow-Headers: Content-Type')
    print('Access-Control-Max-Age: 86400') # Cache for 1 day (86400 seconds)
    print('Vary: Origin')
    print('Cache-Control: no-store')
    method=os.environ.get("REQUEST_METHOD", "").upper()
    cont_type=os.environ.get("CONTENT_TYPE", "").lower()
    cont_len=int(os.environ.get("CONTENT_LENGTH", "0"))
    arguments = cgi.parse()
    if method != 'OPTIONS':
        print('Content-type: application/json')
    if method == 'OPTIONS':
        # Do nothing
        pass
    elif method == 'POST':
        print('Accept: application/json')
        if arguments:
            respond_with_error(400, f"No query parameters are allowd")
        elif cont_type != 'application/json' or cont_len == 0:
            respond_with_error(415, 'Json body required')
        elif cont_len > config.max_email_body_length:
            respond_with_error(413, f'Body must be less or equal to {config.max_email_body_length} bytes')
        body = sys.stdin.read()
        try:
            body_obj = json.loads(body)
        except:
            respond_with_error(400, 'Invalid body')
        if not msg_sent and validate_body(body_obj):
            send_mail(body_obj)
            print('Status: 204')
            print('')
    else:
        respond_with_error(405, f"The method '{method}' is not allowed")
except Exception:
    print(traceback.format_exc(), file=sys.stderr)
    respond_with_error(500, 'Unknown error')

