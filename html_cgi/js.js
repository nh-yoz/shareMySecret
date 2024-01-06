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
        ...errors
    }
    Object.entries(allErrorsId).forEach(([key, value]) => {
        const el = document.getElementById(key);
        const elClassList = el.classList;
        el.innerHTML = value || '&nbsp;';
        value === '&nbsp;' ? elClassList.add('hide') : elClassList.remove('hide');
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
    }
    else if (obj.secret_message.length > 2000) {
        errors['send-message-error'] = "Too many characters (max 2000)";
    }
    
    if (!/^[0-9]+$/.test(obj.max_views)) {
        errors['send-limit-views-error'] = "Must be an integer >= 0";
    }
    if (/^[0-9]+$/.test(obj.expires_in_value) && parseInt(obj.expires_in_value, 10) > 0) {
        const val = parseInt(obj.expires_in_value, 10);
        testObj = { 'd': 30, 'h': 30*24, 'm': 30*24*60 }
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
    if (!validateForm()) { return; }
    throbber.direction = 'crypt'
    showSpinner(true);
    const controller = new AbortController();
    const tOutId = setTimeout(() => controller.abort(), 8000)
    const url = 'sharesecret.cgi?method=post';
    const headers = { "Content-Type": "application/json" }
    fetch(url, { method: "POST", headers, body: JSON.stringify(getJson(true)), signal: controller.signal })
        .then(res => {
            if (res.ok) {
                return res.json();
            }
            return Promise.reject(res);
        }).then(json => {
            clearTimeout(tOutId);
            const link = `${window.location.href.split('?')[0]}?${json.token}`
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
                setErrors({ 'send-error': 'The server took too long to respond. Try again later.' });
            } else {
                setErrors({ 'send-error': 'An error occurred, please try again later.' });
            }
            showSpinner(false);
        })
};

const get = (token) => {
    const controller = new AbortController();
    const tOutId = setTimeout(() => controller.abort(), 8000)
    const url = `sharesecret.cgi?method=get&token=${token}`;
    fetch(url, { method: "GET", signal: controller.signal })
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
            setErrors({ 'get-error-error' : error });
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
    navigator.clipboard.writeText(element.value);
    const old = window.getComputedStyle(element , null).getPropertyValue('background-color'); 
    element.animate([{ backgroundColor: 'white' }, { backgroundColor: old }], { duration: 200 })
}

const showSpinner = (visible) => {
    const spinnerClassList = document.getElementById('throbber-container').classList;
    if (visible) {
        spinnerClassList.remove('no-show')
    } else {
        spinnerClassList.add("no-show");
    }
}

window.addEventListener('load', () => {
    const throbber = new CryptThrobber(document.getElementById('throbber'), 20, 'white', { speedFactor: 0.5 });
    document.getElementById('send-message').addEventListener('input', () => messageChange());
    document.getElementById('send-send').addEventListener('click', () => send());
    document.getElementById('send-result-copy').addEventListener('click', () => copyElementValueToClipboard('send-result-link'));
    document.getElementById('send-result-go-home').addEventListener('click', () => goHome());
    document.getElementById('get-result-copy').addEventListener('click', () => copyElementValueToClipboard('get-result-message'));
    document.getElementById('get-result-go-home').addEventListener('click', () => goHome());
    document.getElementById('get-error-go-home').addEventListener('click', () => goHome());
    const searchString = window.location.search;
    if (searchString !== '') {
        throbber.direction = 'decrypt'
        showSpinner(true)
        get(searchString.slice(1));
    } else {
        setView('send');
    };
})
