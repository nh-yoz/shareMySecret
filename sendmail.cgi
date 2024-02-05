#!/usr/bin/python3
import smtplib, json, collections.abc, traceback, sys, re
from email.message import EmailMessage
from email.utils import make_msgid

smtp_host = 'smtp.example.com'
smtp_port = 465
smtp_ssl = True
smtp_from = 'my_app@example.com'
smtp_auth = True # To authenticate to mail server
smtp_credentials = ('username', 'secret_password')
send_traceback = True # If unexpected error, responds with traceback in json

email_regex = re.compile(r'([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+')

def respond_with_error(status: int, message: str):
    errors = {
        '400': 'Bad Request',
        '401': 'Unauthorized',
        '500': 'Internal Server Error'
    }
    print('Status: ' + str(status) + ' ' + errors[str(status)])
    print('')
    resdict = { 'status': status, 'message': str(message) }
    print(json.JSONEncoder().encode(resdict))
    exit()


def is_valid_email(email: str) -> bool:
    return re.fullmatch(email_regex, email)


def is_string(value) -> bool:
    return type(value) == str


def is_string_array(value) -> bool:
    if not isinstance(value, list):
        return False
    for v in value:
        if not is_string(v):
            return False
    return True


def validate_body(obj):
    test_dict = {
        'addresses': ['an array of email addresses (strings)', is_string_array],
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
    for email_address in obj['addresses']:
        if not is_valid_email(email_address):
            respond_with_error(400, f'{email_address} is not a valid email address')
            return False
    return True


def send_mail(obj):
    global smtp_host, smtp_port, smtp_ssl, smtp_from, smtp_auth, smtp_credentials
    msg = EmailMessage()
    msg['From'] = smtp_from
    msg['To'] = ", ".join(obj['addresses'])
    msg['Subject'] = obj['subject']
    msg.set_content(obj['text_message'])
    asparagus_cid = make_msgid()
    msg.add_alternative(obj['html_message'].format(asparagus_cid=asparagus_cid[1:-1]), subtype='html')
    server = smtplib.SMTP_SSL(smtp_host, smtp_port) if smtp_ssl else smtplib.SMTP(smtp_host, smtp_port)
    if smtp_auth:
        server.login(smtp_credentials[0], smtp_credentials[1])
    server.send_message(msg)



##########################
# Main program
##########################

print('Content-type: application/json')
print('Access-Control-Allow-Origin: https://misc.niklashook.fr')
print('Vary: Origin')
print('Cache-Control: no-store')
try:
    body = sys.stdin.read()
    try:
        body_obj = json.loads(body)
    except:
        respond_with_error(400, 'Invalid body')
        exit()
    if validate_body(body_obj):
        send_mail(body_obj)
        print('Status: 204')
        print('')
except Exception:
    respond_with_error(500, traceback.format_exc() if send_traceback else 'Unknown error')
