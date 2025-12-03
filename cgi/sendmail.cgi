#!/usr/bin/python3
import smtplib, ssl, json, traceback, sys, re, cgi, os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
import config, validation

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

def validate_body(obj):
    test_dict = {
        'from': [ 'and', (('type', 'str' ), ('minmax', '[0,20]')) ],
        'to': [ 'and', (('type', 'list' ), ('minmax', '[1,10]')) ],
        'token': [ ('type', 'str' ), ('minmax', '[53,53]') ]
    }
    try:
        validation.validate_dict(obj, test_dict)
    except Exception as err:
            respond_with_error(400, err)
            return False
    try:
        test_dict = {
            'name': [ 'and', (('type', 'str' ), ('minmax', '[0,20]')) ],
            'email': [ 'email' ],
        }
        for item in test_dict['to']:
            validation.validate_dict(item, test_dict)
    except Exception as err:
            respond_with_error(400, err)
            return False
    # Verify that the secret file exists
    fname = config.secret_files_path + '/' + obj['token'][0:10]
    if not os.path.exists(fname):
        respond_with_error(400, 'Invalid token')
        return False
    return True


def replace_placeholders(text: str, senders_name: str, recipient_name: str, token: str):
    replacements = {
        'senders_name': 'someone' if senders_name.strip() == '' else senders_name.strip(),
        'recipient_name': recipient_name.strip(),
        'site_name': config.site_name,
        'token': token,
        'site_protocol': config.site_protocol,
        'site_domain_name': config.site_domain_name,
        'site_root_path': config.site_root_path,
    }
    for k, v in replacements.items():
        text = text.replace('{{' + k +'}}', v)
    text = re.sub(r' +', ' ', text).replace(' ,', ',')
    return text


def send_mail_old(obj):
    global subject, email_html, email_text
    for recipient in obj['to']:
        msg = MIMEMultipart("alternative")
        msg['From'] = config.smtp_from
        msg['To'] = recipient['email']
        msg['Subject'] = replace_placeholders(subject)
        msg.attach(MIMEText(replace_placeholders(email_text, obj['from'], recipient['name']), obj['token'], 'plain'))
        msg.attach(MIMEText(replace_placeholders(email_html, obj['from'], recipient['name']), obj['token'], 'html'))
        server = smtplib.SMTP_SSL(config.smtp_host, config.smtp_port) if config.smtp_ssl else smtplib.SMTP(config.smtp_host, config.smtp_port)
        if config.smtp_auth:
            server.login(config.smtp_username, config.smtp_password)
        server.send_message(msg)

def send_mail(obj):
    global subject, email_html, email_text
    emails = []
    for recipient in obj['to']:
        msg = EmailMessage()
        msg['From'] = config.smtp_from
        msg['To'] = recipient['email']
        msg['Subject'] = replace_placeholders(subject)
        
        # Required headers for spam filters:
        msg['Date'] = formatdate(localtime=True)
        msg['Message-ID'] = make_msgid(domain="domain.any")

        # Set UTF-8 default
        msg.set_charset('utf-8')

        # Add text + HTML alternative parts
        msg.set_content(replace_placeholders(email_text, obj['from'], recipient['name']), obj['token'], subtype='plain', charset='utf-8')
        msg.add_alternative(replace_placeholders(email_html, obj['from'], recipient['name']), obj['token'], subtype='html', charset='utf-8')
        emails.append(msg)

    # Connect and send
    if config.smtp_ssl:
        # SMTPS (port 465)
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(config.smtp_host, config.smtp_port, context=context) as server:
            if config.smtp_auth:
                server.login(config.smtp_username, config.smtp_password)
            for msg in emails:
                server.send_message(msg)
    else:
        # STARTTLS (e.g., port 587)
        with smtplib.SMTP(config.smtp_host, config.smtp_port) as server:
            server.starttls(context=ssl.create_default_context())
            if config.smtp_auth:
                server.login(config.smtp_username, config.smtp_password)
            for msg in emails:
                server.send_message(msg)



##########################
# Main program
##########################

subject = 'Message sent by {{senders_name}} ready for viewing on {{site_name}}'
email_html= '''
<html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Secret Message Notification</title>
        <style>
            body {
                font-family: Arial, Helvetica, sans-serif;
                line-height: 1.6em;
                color: #333333; /* Dark gray text */
            }
            .button {
                display: inline-block;
                padding: 10px 20px;
                margin: 15px 0;
                background-color: #007bff; /* Professional blue */
                color: #ffffff !important;
                text-decoration: none;
                border-radius: 4px;
            }
            p.footer {
                font-size: 0.9em;
                color: #777777;
            }
            a {
                color: #007bff;
            }
            hr {
                border: 0;
                border-top: 1px solid #eeeeee;
                margin: 20px 0;
            }
        </style>
    </head>
    <body>
        <p>Hello {{recipient_name}},</p> 
        <p>This is an automatic email to notify you that a secure private message has been sent to you by {{senders_name}} via **{{site_name}}** ({{site_domain_name}}).</p>
        <p>If you don't know this sender or didn't expect to receive this message, feel free to ignore it.</p>
        <p>To view your message, click the link below:</p>
        <a href="{{site_protocol}}://{{site_domain_name}}{{site_root_path}}index.html#{{token}}" class="button">View Secret Message</a>
        <p>Please note: This message will self-destruct after a certain time or number of views (defined by the sender).</p>
        <hr>
        <p class="footer">
            Want to send secure messages? Visit <a href="{{site_protocol}}://{{site_domain_name}}{{site_root_path}}index.html">{{site_protocol}}://{{site_domain_name}}{{site_root_path}}</a>.
        </p>
        </body>
</html>
'''
email_text = '''
        Hello {{recipient_name}},

        This is an automatic email to notify you that a secure private message has been sent to you by {{senders_name}} via **{{site_name}}** ({{site_domain_name}}).

        If you don't know this sender or didn't expect to receive this message, feel free to ignore it.

        To view your message, copy the link below in your browser's address bar:
        {{site_protocol}}://{{site_domain_name}}{{site_root_path}}index.html#{{token}}
        
        Please note: This message will self-destruct after a certain time or number of views (defined by the sender).

        Want to send secure messages? Visit {{site_protocol}}://{{site_domain_name}}{{site_root_path}}.
'''



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

