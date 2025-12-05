#!/usr/bin/python3
import smtplib, ssl, json, traceback, sys, re
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
import config, validation, common
from common import request as req



def validate_body(obj):
    test_dict = {
        'from': [ 'and', (('type', 'str' ), ('minmax', '[0,35]')) ],
        'to': [ 'and', (('type', 'list' ), ('minmax', '[1,10]')) ],
        'token': [ ('type', 'str' ), ('minmax', '[53,53]') ]
    }
    try:
        validation.validate_dict(obj, test_dict)
    except Exception as err:
        common.respond_with_error(400, err)
        return False
    try:
        test_dict = {
            'name': [ 'and', (('type', 'str' ), ('minmax', '[0,35]')) ],
            'email': [ 'and', ('email', ('max', 320)) ],
        }
        for item in obj['to']:
            validation.validate_dict(item, test_dict)
    except Exception as err:
        common.respond_with_error(400, err)
        return False
    return common.validate_token(obj['token'])


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


def send_mail(obj):
    global subject, email_html, email_text
    emails = []
    for recipient in obj['to']:
        msg = EmailMessage()
        msg['From'] = config.smtp_from
        msg['To'] = recipient['email']
        msg['Subject'] = replace_placeholders(subject, obj['from'], recipient['name'], obj['token'])
        
        # Required headers for spam filters:
        msg['Date'] = formatdate(localtime=True)
        msg['Message-ID'] = make_msgid(domain="domain.any")

        # Set UTF-8 default
        msg.set_charset('utf-8')

        # Add text + HTML alternative parts
        msg.set_content(replace_placeholders(email_text, obj['from'], recipient['name'], obj['token']), subtype='plain', charset='utf-8')
        msg.add_alternative(replace_placeholders(email_html, obj['from'], recipient['name'], obj['token']), subtype='html', charset='utf-8')
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
        <title>Secure Message Notification</title>
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
        <p>This is an automated email to let you know that {{senders_name}} has sent you a secure private message via **{{site_name}}** ({{site_domain_name}}).</p>
        <p>If you do not know the sender or were not expecting this message, you can safely ignore it.</p>
        <p>To view your message, click the link below:</p>
        <a href="{{site_protocol}}://{{site_domain_name}}{{site_root_path}}index.html#{{token}}" class="button">View Secret Message</a>
        <p>Please note: This message will self-destruct after a certain amount of time or number of views, as defined by the sender.</p>
        <hr>
        <p class="footer">
            Want to send secure messages yourself? Visit <a href="{{site_protocol}}://{{site_domain_name}}{{site_root_path}}index.html">{{site_protocol}}://{{site_domain_name}}{{site_root_path}}</a>.
        </p>
        </body>
</html>
'''
email_text = '''
        Hello {{recipient_name}},

        This is an automated email to let you know that {{senders_name}} has sent you a secure private message via **{{site_name}}** ({{site_domain_name}}).

        If you do not know the sender or were not expecting this message, you can safely ignore it.

        To view your message, copy the link below to your browser's address bar:
        {{site_protocol}}://{{site_domain_name}}{{site_root_path}}index.html#{{token}}
        
        Please note: This message will self-destruct after a certain amount of time or number of views, as defined by the sender.

        Want to send secure messages yourself? Visit {{site_protocol}}://{{site_domain_name}}{{site_root_path}}.
'''


try:
    common.print_headers(methods = ['POST', 'OPTIONS'])
    if req.method == 'OPTIONS':
        common.respond(200, '')
    elif req.method == 'POST':
        print('Content-type: application/json')
        if req.arguments:
            common.respond_with_error(400, f"No query parameters are allowed")
        elif req.content.type != 'application/json' or req.content.length == 0:
            common.respond_with_error(415, 'Json body required')
        elif req.content.length > config.max_email_body_length:
            common.respond_with_error(413, f'Body must be less or equal to {config.max_email_body_length} bytes')
        body = sys.stdin.read()
        try:
            body_obj = json.loads(body)
        except:
            common.respond_with_error(400, 'Invalid json body')
            exit()
        if validate_body(body_obj):
            send_mail(body_obj)
            common.respond(204)
    else:
        common.respond_with_error(405, f"The method '{req.method}' is not allowed")
except Exception:
    print(traceback.format_exc(), file=sys.stderr)
    common.respond_with_error(500, 'Unknown error')

