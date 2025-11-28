const setView = (id) => {
    const allViewsId = {
        'get-result': false,
        'get-error': false,
        'send-result': false,
        'send': false
    };
    if (id !== '') {
        allViewsId[id] = true;
    }
    Object.entries(allViewsId).forEach(([key, value]) => {
        const elClassList = document.getElementById(key).classList;
        value ? elClassList.remove('no-show') : elClassList.add('no-show');
    })
}

const setErrors = (errors) => {
    const allErrorsId = {
        'send-message-error': '',
        'send-limit-views-error': '',
        'send-expires-error': '',
        'send-error': '',
        'get-error-error': '',
        'send-result_email-address_error': '',
        'pwd-form-length-error': '',
        'pwd-form-number-error': '',
        'pwd-form-special-error': '',
        'pwd-form-numbers-error': '',
        'pwd-form-error': '',
        ...errors
    }
    Object.entries(allErrorsId).forEach(([key, value]) => {
        const el = document.getElementById(key);
        const elClassList = el.classList;
        el.innerHTML = value || '&nbsp;';
        ['&nbsp;', ''].includes(value) ? elClassList.add('hide') : elClassList.remove('hide');
    })
}

const getJson = (parse = false) => {
    const obj = {
        secret_message: document.getElementById('send-message').value,
        max_views: document.getElementById('send-limit-views').value,
        expires_in_value: document.getElementById('send-expires-value').value,
        expires_in_unit: document.getElementById('send-expires-unit').value
    }
    if (parse) {
        obj.max_views = parseInt(obj.max_views, 10);
        obj.expires_in_value = parseInt(obj.expires_in_value, 10);
    }
    return obj;
}

const validateForm = () => {
    const obj = getJson();
    const errors = {};
    if (obj.secret_message.length === 0) {
        errors['send-message-error'] = "May not be empty";
    } else if (obj.secret_message.length > 2000) {
        errors['send-message-error'] = "Too many characters (max 2000)";
    }

    if (!/^[0-9]+$/.test(obj.max_views)) {
        errors['send-limit-views-error'] = "Must be an integer >= 0";
    }
    if (/^[0-9]+$/.test(obj.expires_in_value) && parseInt(obj.expires_in_value, 10) > 0) {
        const val = parseInt(obj.expires_in_value, 10);
        testObj = {
            'd': 30,
            'h': 30 * 24,
            'm': 30 * 24 * 60
        }
        if (val > testObj[obj.expires_in_unit]) {
            errors['send-expires-error'] = "Must at most be 30 days";
        }
    } else {
        errors['send-expires-error'] = "Must be a positive integer";
    }
    setErrors(errors);
    return Object.keys(errors).length === 0;
}

const send = () => {
    if (!validateForm()) {
        return;
    }
    throbber.direction = 'crypt'
    showSpinner(true);
    const controller = new AbortController();
    const tOutId = setTimeout(() => controller.abort(), 8000)
    const url = 'sharesecret.cgi?action=encrypt';
    const headers = {
        "Content-Type": "application/json",
        "Origin": window.location.hostname,
        "X-Requested-With": window.location.hostname
    }
    fetch(url, {
            method: "POST",
            headers,
            body: JSON.stringify(getJson(true)),
            signal: controller.signal
        })
        .then(res => {
            if (res.ok) {
                return res.json();
            }
            return Promise.reject(res);
        }).then(json => {
            clearTimeout(tOutId);
            const link = `${window.location.href.split('?')[0]}#${json.token}`
            document.getElementById('send-result-link').value = link
            // console.log(json)
            document.getElementById('send-message').value = ''
            setView('send-result');
            showSpinner(false);
        })
        .catch(err => {
            // console.log(err);
            clearTimeout(tOutId);
            if (err.name && err.name === 'AbortError') {
                setErrors({
                    'send-error': 'The server took too long to respond. Try again later.'
                });
            } else {
                setErrors({
                    'send-error': 'An error occurred, please try again later.'
                });
            }
            showSpinner(false);
        })
};

const get = (token) => {
    const controller = new AbortController();
    const tOutId = setTimeout(() => controller.abort(), 8000)
    const url = 'sharesecret.cgi?action=decrypt';
    const headers = {
        "Content-Type": "application/json",
        "Origin": window.location.hostname,
        "X-Requested-With": window.location.hostname
    }
    fetch(url, {
            method: "POST",
            headers,
            body: JSON.stringify( { token }),
            signal: controller.signal
        })
        .then(res => {
            if (res.ok) {
                return res.json();
            }
            return Promise.reject(res);
        }).then(json => {
            clearTimeout(tOutId);
            expires = new Date(json.expires_at);
            document.getElementById('get-result-message').value = json.message;
            document.getElementById('get-result-views').innerHTML = `Views: ${json.views}${json.max_views === 0 ? '' : ` / ${json.max_views}`}`;
            document.getElementById('get-result-expires').innerHTML = `Expires: ${expires.toLocaleDateString('en-GB', { year: 'numeric', month: 'short', day: 'numeric' })} ${expires.toLocaleTimeString('en-GB')}`;
            setView('get-result');
            showSpinner(false);
        })
        .catch(err => {
            clearTimeout(tOutId);
            let error = '';
            if ([400, 404, 410].includes(err.status)) {
                error = 'Your token is invalid or the message has expired.';
            } else {
                if (err.name && err.name === 'AbortError') {
                    error = 'The server took too long to respond. Try again later.'
                } else {
                    error = 'The server encountered an error while treating the request. Try again later.'
                }
            }
            setErrors({
                'get-error-error': error
            });
            setView('get-error');
            showSpinner(false);
        })
};

const messageChange = () => {
    document.getElementById('send-message-char').innerHTML = `${document.getElementById('send-message').value.length}/2000`;
}

const goHome = () => {
    window.location = `${window.location.href.split('?')[0]}`
}

const copyElementValueToClipboard = (id) => {
    const element = document.getElementById(id);
    let text = element.value
    if (text === undefined) {
        text = element.textContent
    }
    navigator.clipboard.writeText(text);
    const old = window.getComputedStyle(element, null).getPropertyValue('background-color');
    element.animate([{
        backgroundColor: 'white'
    }, {
        backgroundColor: old
    }], {
        duration: 200
    })
}

const showSpinner = (visible) => {
    const spinnerClassList = document.getElementById('throbber-container').classList;
    if (visible) {
        spinnerClassList.remove('no-show')
    } else {
        spinnerClassList.add("no-show");
    }
}

const sendEmail = () => {
    const errEl = document.getElementById('send-result_email-address_error');
    const resultElement = document.getElementById('send-result_email-result');
    resultElement.innerHTML = '&nbsp;';
    const emailsElement = document.getElementById('send-result-email-addresses');
    const emails = emailsElement.value.split(/;|:|,| /g).filter(val => val !== '');
    const subject = document.getElementById('send-result-email-subject').value;
//    const sender = document.getElementById('send-result-email-sender').value;
    const errors = {};
    const emailsOk = emails.every(email => {
        if (/^([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Za-z]{2,})+$/.test(email)) {
            console.log(`email ${email} ok`);
            return true;
        } else {
            console.log(`email ${email} not ok`);
            errors['send-result_email-address_error'] = `"${email}" is not a valid email address`;
            return false;
        }
    })

    setErrors(errors);
    if (emailsOk) {
        showSpinner(true);
        const controller = new AbortController();
        const tOutId = setTimeout(() => controller.abort(), 8000);
        const url = `sendmail.cgi`;
        const headers = {
	    "Content-Type": "application/json",
	    "Origin": window.location.hostname,
	    "X-Requested-With": window.location.hostname
        }
        const body = {
            to: emails,
            subject,
            text_message: `Hello,\n\n
                A secret message has been sent to you via ${window.location.hostname}. To view the message, use the link below.\n\n
                ${document.getElementById('send-result-link').value}\n\n\n
                Want to send secret messages? Visit ${window.location.href}`,
            html_message: btoa(`<html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <style>
                        body {
                            /* background-color: black;
                            color: greenyellow; */
                            font-family: Arial, Helvetica, sans-serif;
                            line-height: 1.4em;
                        }
                        /* p, a { font-size: 1rem; color: inherit; } */
                    </style>
                </head>
                <body>
                    <p>Hello,</p>
                    <p>A secret message has been sent to you via ${window.location.hostname}.</p>
                    <p>To view the message, click <a href="${document.getElementById('send-result-link').value}">here</a>.</p>
                    <p>---<br>Want to send secret messages ? Visit <a href="${window.location.href}">${window.location.href}</a>.</p>
                </body>
            </html>`)
        };
        fetch(url, {
                method: "POST",
		headers,
                signal: controller.signal,
                body: JSON.stringify(body)
            })
            .then(res => {
                if (res.ok) {
                    resultElement.innerHTML = 'The email has been sent';
                    emailsElement.value = '';
                    resultElement.classList.add('info');
                    resultElement.classList.remove('error');
                } else {
                    return Promise.reject(res);
                }
            })
            .catch(err => {
                let error = '';
                if (err.name && err.name === 'AbortError') {
                    error = 'The server took too long to respond. Try again later.'
                } else {
                    error = 'The server encountered an error. Try again later.'
                }
                resultElement.innerHTML = error;
                resultElement.classList.add('error');
                resultElement.classList.remove('info');
            })
            .finally(() => {
                clearTimeout(tOutId);
                showSpinner(false);
            })

    }
}

const showPwdGenerator = (show) => {
    const elements = [{
        el: document.getElementById('pwd-form'),
        show: true
    }, {
        el: document.getElementById('svg-pwd-open'),
        show: true
    }, {
        el: document.getElementById('svg-pwd-closed'),
        show: false
    }]
    elements.forEach(item => {
        if (item.show === show) {
            item.el.classList.remove('no-show')
        } else {
            item.el.classList.add('no-show')
        }
    })
}

const validatePwdForm = () => {
    let isOk = true;
    const errors = {};
    const retObj = { length: 0, upper: 0, lower: 0, number: 0, special: 0, ignoreAmbigious: 0 };
    const numberInputArr = ['pwd-form-length', 'pwd-form-number', 'pwd-form-special']
        .map(id => ({
            id,
            value: document.getElementById(id).value,
            errId: `${id}-error`
        }));
    numberInputArr.forEach(obj => {
        const val = obj.value;
        if (!/^[0-9]+$/.test(val) || parseInt(val) < 0) {
            isOk = false;
            errors[obj.errId] = 'Not integer >= 0';
        } else {
            obj.value = parseInt(obj.value);
        }
    });
    if (isOk) {
        if (numberInputArr.find(obj => obj.id === 'pwd-form-length').value > 200) {
            isOk = false;
            errors['pwd-form-length-error'] = 'Must be <= 200';
        }
    }
    if (['pwd-form-option-upper', 'pwd-form-option-lower', 'pwd-form-option-numbers', 'pwd-form-option-special']
        .every(id => !document.getElementById(id).checked)) {
        errors['pwd-form-error'] = 'At least one character-type option must be checked.';
        isOk = false;
    }
    if (isOk) {
        // Creating retObj
        Object.entries({
                'pwd-form-option-numbers': 'pwd-form-number',
                'pwd-form-option-special': 'pwd-form-special'
            })
            .forEach(([key, value]) => {
                if (!document.getElementById(key).checked) {
                    numberInputArr.find(obj => obj.id === value).value = 0;
                }
            });
        retObj.length = numberInputArr.find(obj => obj.id === 'pwd-form-length').value;
        retObj.number = Math.max(document.getElementById('pwd-form-option-numbers').checked ? 1 : 0, numberInputArr.find(obj => obj.id === 'pwd-form-number').value);
        retObj.special = Math.max(document.getElementById('pwd-form-option-special').checked ? 1 : 0, numberInputArr.find(obj => obj.id === 'pwd-form-special').value);
        retObj.upper = document.getElementById('pwd-form-option-upper').checked ? 1 : 0;
        retObj.lower = document.getElementById('pwd-form-option-lower').checked ? 1 : 0;
        retObj.ignoreAmbigious = document.getElementById('pwd-form-option-ambiguous').checked ? 1 : 0;
        if (Object.entries(retObj).reduce((acc, [key, value]) => acc + (key === 'length' ? value : -value), 0) < 0) {
            errors['pwd-form-numbers-error'] = 'Password length is less than minimums and options.';
            isOk = false;
        }
    }
    setErrors(errors);
    return isOk ? retObj : false;
}

const getPassword = (length, upper, lower, number, special, ignoreAmbigious) => {
    const getRandomChars = (chars, count) => {
        const valueArr = window.crypto.getRandomValues(new Uint8Array(count));
        return valueArr.reduce((acc, cur) => `${acc}${chars[Math.trunc(cur / 256 * chars.length)]}`, '');
    }

    const shuffleString = (str) => {
        const charArr = str.split('');
        const valueArr = window.crypto.getRandomValues(new Uint8Array(charArr.length));
        for (let i = charArr.length - 1; i > 0; i--) {
            const randomValue = Math.trunc(valueArr[i] / 256 * i);
            [charArr[i], charArr[randomValue]] = [charArr[randomValue], charArr[i]];
        }
        return charArr.join('');
    }

    const charSet = [
        { name: 'upper', chars: 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', min: upper, count: 0, class: ''},
        { name: 'lower', chars: 'abcdefghijklmnopqrstuvwxyz', min: lower, count: 0, class:'' },
        { name: 'number', chars: '0123456789', min: number, count: 0, class: 'pwd-number' },
        { name: 'special', chars: '!@#$()[]{}%^&*_-=', min: special, count: 0, class: 'pwd-special' },
    ]
    if (ignoreAmbigious) {
        charSet.forEach(obj => obj.chars = obj.chars.replace(/[|Il10O]/g, ''));
    }
    const [chars, initPwd] = charSet.reduce((acc, cur) => [`${acc[0]}${cur.min > 0 ? cur.chars : ''}`, `${acc[1]}${getRandomChars(cur.chars, cur.min)}`], ['', '']);
    const pwd = shuffleString(`${initPwd}${getRandomChars(chars, length - initPwd.length)}`);
    const html = pwd.split('').reduce((acc, cur) => {
        let t = '';
        charSet.every(item => {
            if (item.chars.includes(cur)) {
                t = `<span class="${item.class}">${cur}</span>`;
                return false;
            } else {
                return true;
            }
        });
        return `${acc}${t}`;
    }, '');

    return {
        password: pwd,
        strength: Math.round(Math.log2(charSet.reduce((acc, cur) => acc + cur.chars.length * Math.min(cur.min, 1), 0) ** length)),
        html
    };
}

const generatePassword = () => {
    const retVal = validatePwdForm();
    if (!retVal) {
        document.getElementById('pwd-result').innerHTML = '&nbsp;';
        document.getElementById('pwd-strength').innerHTML = ''
    } else {
        pwdObj = getPassword(retVal.length, retVal.upper, retVal.lower, retVal.number, retVal.special, retVal.ignoreAmbigious);
        document.getElementById('pwd-result').innerHTML = pwdObj.html;
        if (pwdObj.strength > 1000) {
            document.getElementById('pwd-strength').innerHTML = '> 1000 (insane)';
        } else {
            document.getElementById('pwd-strength').innerHTML = `${pwdObj.strength} (${Object.entries({'very weak': 20, 'weak': 45, 'reasonable': 65, 'strong': 100, 'very strong': 130, 'extremely strong': 500, 'insane': 1001, 'insane': Infinity})
                .reduce((acc, [key, value]) => acc !== '' ? acc : pwdObj.strength < value ? key : '', '')})`;
        }
    }
}

window.addEventListener('load', () => {
    const throbber = new CryptThrobber(document.getElementById('throbber'), 20, 'white', {
        speedFactor: 0.5
    });
    document.getElementById('send-message').addEventListener('input', () => messageChange());
    document.getElementById('send-send').addEventListener('click', () => send());
    document.getElementById('send-result-copy').addEventListener('click', () => copyElementValueToClipboard('send-result-link'));
    document.getElementById('send-result-email').addEventListener('click', sendEmail);
    document.getElementById('send-result-go-home').addEventListener('click', goHome);
    document.getElementById('get-result-copy').addEventListener('click', () => copyElementValueToClipboard('get-result-message'));
    document.getElementById('get-result-go-home').addEventListener('click', goHome);
    document.getElementById('get-error-go-home').addEventListener('click', goHome);
    document.getElementById('svg-pwd-open').addEventListener('click', () => showPwdGenerator(false));
    document.getElementById('svg-pwd-closed').addEventListener('click', () => showPwdGenerator(true));
    document.getElementById('pwd-copy').addEventListener('click', () => copyElementValueToClipboard('pwd-result'));
    ['pwd-form-length', 'pwd-form-number', 'pwd-form-special'].forEach(id => {
        const el = document.getElementById(id);
        el.addEventListener('change', generatePassword);
        el.addEventListener('keyup', generatePassword);
    });
    [
        'pwd-form-option-upper',
        'pwd-form-option-lower',
        'pwd-form-option-numbers',
        'pwd-form-option-special',
        'pwd-form-option-ambiguous',
        'pwd-send'
    ].forEach(id => document.getElementById(id).addEventListener('click', generatePassword));
    document.getElementById('send-result-email-addresses').value = '';
    const hash = window.location.hash.substring(1);
    if (hash !== '') {
        throbber.direction = 'decrypt'
        showSpinner(true)
        get(hash);
    } else {
        setView('send');
    };
    generatePassword();
})
