let throbber;
const maxFileSize = 1 * 1024 * 1024 // 1 Mb

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
    });
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
    };
    Object.entries(allErrorsId).forEach(([key, value]) => {
        const el = document.getElementById(key);
        const elClassList = el.classList;
        el.innerHTML = value || '&nbsp;';
        ['&nbsp;', ''].includes(value) ? elClassList.add('hide') : elClassList.remove('hide');
    });
}

const getJson = (parse = false) => {
    const obj = {
        message: document.getElementById('send-message').value,
        max_views: document.getElementById('send-limit-views').value,
        expires_in_value: document.getElementById('send-expires-value').value,
        expires_in_unit: document.getElementById('send-expires-unit').value
    };
    if (parse) {
        obj.max_views = parseInt(obj.max_views, 10);
        obj.expires_in_value = parseInt(obj.expires_in_value, 10);
    }
    return obj;
}

const isFileOk = () => {
    const maxSize = maxFileSize; // 5 MB in bytes
    const file = document.getElementById('send-file').files[0];
    if (!file) {
        return true;
    }
    return file.size <= maxSize;
}

const getHumanSize = (sizeBytes) => {
    if (sizeBytes <= 0) return '0 B';
    return [ 'B', 'kB', 'MB', 'GB' ].map((unit, i) => [ Math.round(10 * sizeBytes / (1024 ** i)) / 10, unit ])
        .filter(item => item[0] > 0.99).reverse()[0].join('&nbsp;');
}

const fileChange = () => {
    const file = document.getElementById('send-file').files[0];
    const [ filenameEl, fileErrEl ] = ['send-file-filename', 'send-file-error'].map(id => document.getElementById(id));
    const maxSize = maxFileSize; // 10 MB in bytes
    if (!file) {
        filenameEl.textContent = "No file selected";
        return;
    }
    filenameEl.innerHTML = `${file.name} (${getHumanSize(file.size)})` 
    if (file.size > maxSize) {
        fileErrEl.textContent = "File exceeds 10 MB limit!";
    } else {
        fileErrEl.innerHTML = "&nbsp;";
    }
}

const validateForm = () => {
    const obj = getJson();
    const errors = {};
    if (obj.message.length === 0) {
        errors['send-message-error'] = "May not be empty";
    } else if (obj.message.length > 2000) {
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
        };
        if (val > testObj[obj.expires_in_unit]) {
            errors['send-expires-error'] = "Must at most be 30 days";
        }
    } else {
        errors['send-expires-error'] = "Must be a positive integer";
    }
    setErrors(errors);
    return Object.keys(errors).length === 0 && isFileOk();
}

const getJsonWithFile = async () => {
    const json = getJson(true);
    json['file'] = null;
    const file = document.getElementById('send-file').files[0];
    if (file) {
        const reader = new FileReader();
        let resolveFunc, rejectFunc;
        const retPromise = new Promise((resolve, reject) => {
            resolveFunc = resolve;
            rejectFunc = reject;
        });
        reader.onload = async ()  => {
            const base64Data = reader.result.split(',')[1]; // remove data: header
            json['file'] = {
                name: file.name,
                size: file.size,
                data: base64Data
            };
            resolveFunc(json);
        }
        reader.readAsDataURL(file);
        return retPromise;
    } else {
        return new Promise(resolve => resolve(json));
    }
}

// Function to encode a UTF-8 string to Base64
function utf8ToBase64(str) {
    const encoder = new TextEncoder();
    const data = encoder.encode(str);
    const binaryString = String.fromCharCode.apply(null, data);
    return btoa(binaryString);
}

// Function to decode a Base64 string to UTF-8
function base64ToUtf8(b64) {
    const binaryString = atob(b64);
    // Create a Uint8Array from the binary string.
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
    }
    const decoder = new TextDecoder();
    return decoder.decode(bytes);
}

const send = async () => {
    console.log('send');
    if (!validateForm()) {
        console.log('not validated');
        return;
    }
    throbber.direction = 'crypt';
    showSpinner(true);
    const controller = new AbortController();
    const json = await getJsonWithFile()
    const tOutId = setTimeout(() => controller.abort(), 10000 + (json.file !== null ? json.file.size / 1024 * 4 : 0));
    const url = '/cgi/sharesecret.cgi?action=encrypt';
    const headers = {
        "Content-Type": "application/json",
        "Origin": window.location.hostname,
        "X-Requested-With": window.location.hostname
    };
    json.message = utf8ToBase64(json.message);
    fetch(url, {
            method: "POST",
            headers,
            body: JSON.stringify(json),
            signal: controller.signal
        })
        .then(res => {
            if (res.ok) {
                return res.json();
            }
            return Promise.reject(res);
        }).then(json => {
            clearTimeout(tOutId);
            const link = `${window.location.href.split('?')[0]}#${json.token}`;
            document.getElementById('send-result-link').value = link;
            // console.log(json)
            document.getElementById('send-message').value = '';
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
    const tOutId = setTimeout(() => controller.abort(), 15000);
    const url = '/cgi/sharesecret.cgi?action=decrypt';
    const headers = {
        "Content-Type": "application/json",
        "Origin": window.location.hostname,
        "X-Requested-With": window.location.hostname
    };
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
            expires = new Date(json.expires * 1000);
            document.getElementById('get-result-message').value = base64ToUtf8(json.message);
            document.getElementById('get-result-views').innerHTML = `Views: ${json.views}${json.max_views === 0 ? '' : ` / ${json.max_views}`}`;
            document.getElementById('get-result-expires').innerHTML = `Expires: ${expires.toLocaleDateString('en-GB', { year: 'numeric', month: 'short', day: 'numeric' })} ${expires.toLocaleTimeString('en-GB')}`;
            const resFileEl = document.getElementById('get-result-file');
            try {
                if (json.file) {
                    const [ linkEl, fileSizeEl ] = ['get-result-file-link', 'get-result-file-size'].map(id => document.getElementById(id));
                    linkEl.href = "data:application/octet-stream;base64," + json.file.data;
                    linkEl.download = json.file.name;
                    linkEl.textContent = json.file.name;
                    fileSizeEl.innerHTML = `&nbsp;(${getHumanSize(json.file.size)})`;
                    resFileEl.classList.remove('no-show');
                } else {
                    resFileEl.classList.add('no-show');
                }
            } catch (e) {
                console.log(e);
            }
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
                    error = 'The server took too long to respond. Try again later.';
                } else {
                    error = 'The server encountered an error while treating the request. Try again later.';
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
    window.location = window.location.pathname;
}

const copyElementValueToClipboard = (id) => {
    const element = document.getElementById(id);
    let text = element.value;
    if (text === undefined) {
        text = element.textContent;
    }
    navigator.clipboard.writeText(text);
    const old = window.getComputedStyle(element, null).getPropertyValue('background-color');
    element.animate([{
        backgroundColor: 'white'
    }, {
        backgroundColor: old
    }], {
        duration: 200
    });
}

const showSpinner = (visible) => {
    const spinnerClassList = document.getElementById('throbber-container').classList;
    if (visible) {
        spinnerClassList.remove('no-show');
        throbber.isRunning = true;
    } else {
        spinnerClassList.add("no-show");
        throbber.isRunning = false;
    }
}


const removeEmailField = (event) => {
    event.currentTarget.parentElement.parentElement.remove();
}

const addEmailField = (event = null) => {
    const tbodyEl = document.querySelector('table#send-result-email-recipients tbody')
    if (tbodyEl.children.length > 9) {
        return
    }
    const newEl = document.createElement('tr');
    newEl.innerHTML = `
        <td>
            <svg class="add" focusable="false" aria-hidden="true" viewBox="0 0 24 24"><path d="M13 7h-2v4H7v2h4v4h2v-4h4v-2h-4zm-1-5C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2m0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8"></path></svg>
            <svg class="remove" focusable="false" aria-hidden="true" viewBox="0 0 24 24"><path d="M7 11v2h10v-2zm5-9C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2m0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8"></path></svg>
        </td>
        <td class="">
            <input type="text" class="" spellcheck="false" maxlength="35" value="">
        </td>
        <td>
            <input type="email" class="" spellcheck="false" maxlength="320" value="">
        </td>`;
    newEl.querySelector('svg.add').addEventListener('click', addEmailField)
    newEl.querySelector('svg.remove').addEventListener('click', removeEmailField)
    if (event === null) {
        if (tbodyEl.lastChild == null) {
            tbodyEl.appendChild(newEl);
        } else {
            tbodyEl.lastChild.after(newEl);
        }
    } else {
        event.currentTarget.parentElement.parentElement.after(newEl);
    }
}


const validateSendEmailFields = () => {
    let hasErrors = false;
    let from = '';
    const [ linkEl, senderEl, tableEl, errEl ] = ['link', 'email-sender', 'email-recipients', 'email-recipients-err' ]
        .map(suffix => document.getElementById(`send-result-${suffix}`));
    [ linkEl, senderEl ].forEach(el => el.classList.remove('error'));
    linkEl.value = 'https://secret.niklashook.fr/#RQGx8jxrJSOmUE13aLF7n_x-QVKGX1Ly74JCOZs4OJcNKrNzMBr3Y'
    const token = linkEl.value.split('#').reduce((acc, cur, i) => i == 1 ? cur : acc, '' );
    if (token.length !== 53 ) {
        hasErrors = true;
        linkEl.classList.add('error')
    }
    senderEl.value = senderEl.value.trim();
    if (senderEl.value.length > 35) {
        hasErrors = true;
        senderEl.classList.add('error');
    } else {
        from = senderEl.value;
    }
    errEl.classList.add('no-show');
    const emails = [];
    tableEl.querySelectorAll('input[type="text"]').forEach(el => {
        el.classList.remove('error');
        el.value = el.value.trim();
        if (el.value.length > 35) {
            hasErrors = true;
            el.classList.add('error');
            emails.push({ 'name': '' });
        } else {
            emails.push({ 'name': el.value });
        }
    })
    const email_regex = /^([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+$/
    tableEl.querySelectorAll('input[type="email"]').forEach((el, i) => {
        el.classList.remove('error');
        el.value = el.value.trim();
        if (email_regex.test(el.value) && el.value.length <= 320) {
            emails[i]['email'] = el.value;
        } else {
            hasErrors = true;
            el.classList.add('error');
            emails[i]['email'] = '';
        }
    })
    if (hasErrors) {
        errEl.classList.remove('no-show');
    }
    return { hasErrors, obj: { token, from, to: emails.filter(item => item.email !== '') } };
}


const sendEmail = () => {
    const errEl = document.getElementById('send-result_email-address_error');
    const resultElement = document.getElementById('send-result_email-result');
    resultElement.innerHTML = '&nbsp;';
    const validationObj = validateSendEmailFields();

    if (!validationObj.hasErrors) {
        showSpinner(true);
        const controller = new AbortController();
        const tOutId = setTimeout(() => controller.abort(), 10000);
        const url = `/cgi/sendmail.cgi`;
        const headers = {
	    "Content-Type": "application/json",
	    "Origin": window.location.hostname,
	    "X-Requested-With": window.location.hostname
        };
        const body = validationObj.obj;
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
                    error = 'The server took too long to respond. Try again later.';
                } else {
                    error = 'The server encountered an error. Try again later.';
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
    ];
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
        document.getElementById('pwd-strength').innerHTML = '';
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

const decrypt = () => {
    const hash = window.location.hash.substring(1);
    if (hash !== '') {
        throbber.direction = 'decrypt';
        showSpinner(true);
        history.replaceState(null, "", window.location.pathname + window.location.search);
        get(hash);
    }
}

window.addEventListener('load', () => {
    throbber = new CryptThrobber(document.getElementById('throbber'), 20, 'white', {
        speedFactor: 0.5
    });
    document.getElementById('send-message').addEventListener('input', () => messageChange());
    document.getElementById('send-file').addEventListener('change', fileChange);
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
    window.addEventListener('hashchange', decrypt);

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
    if (window.location.hash.substring(1) !== '') {
        decrypt()
    } else {
        setView('send');
    };
    generatePassword();
    addEmailField();
})
