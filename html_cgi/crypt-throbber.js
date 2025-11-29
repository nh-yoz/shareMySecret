
class CryptThrobber {
    #runAnimation = false;
    #changeDirection = false;
    #running = false;

    #nbChars = 0;

    #digits = ['0', '1'];
    #chars = (() => {
        const arr = [];
        for (let i = 65; i < 91 ; i++) {
            const char = String.fromCharCode(i)
            arr.push(char)
            arr.push(char.toLowerCase())
        }
        return arr;
    })()

    #wrapper;
    #textElement;
    #hotspot;

    #options = { // options populated with default values
        direction: 'crypt', // 'crypt' || 'decrypt'
        speedFactor: 1,
        runAnimation: true,
    }

    constructor (containerElement, length, hotspotColor, options = this.#options) {
        if (options) {
            this.#options = { ...this.#options, ...options };
        }

        const idIdx = ((a, i) => {
            while (document.getElementById(a + i) !== null) { i++; }
            return i;
        })('crypt-throbbler-wrapper-', 1)

        const createChildDivs = (parent, ids) => {
            const isArr = Array.isArray(ids);
            const retArr = (isArr ? ids : [ids]).map((id) => {
                const newElement = parent.appendChild(document.createElement('div'));
                newElement.id = id;
                return newElement;
            })
            return isArr ? retArr : retArr[0];
        }

        this.#wrapper = createChildDivs(containerElement, `crypt-throbbler-wrapper-${idIdx}`);
        [this.#textElement, this.#hotspot] = createChildDivs(this.#wrapper, [`crypt-throbbler-text-${idIdx}`, `crypt-throbbler-hotspot-${idIdx}`]);

        [this.#wrapper, this.#textElement, this.#hotspot].forEach(element => {
            element.style.padding = 0;
            element.style.margin = 0;
            element.style.letterSpacing = 0;
            element.style.lineHeight = '1em';
            element.style.position = 'relative';
            element.style.fontFamily = "monospace, 'Courier New', Courier";
            element.style.top = 0;
            element.style.left = 0;
            element.style.fontSize = '1em'
        });
        this.#wrapper.style.overflow = 'clip';
        this.#wrapper.style.height = `calc(${window.getComputedStyle(this.#wrapper).fontSize}*1.1)`;
        this.#textElement.style.left = this.#options.direction === 'crypt' ? '-1ch' : '-2ch';
        this.#hotspot.style.backgroundColor = hotspotColor;
        this.#hotspot.style.position = 'absolute';
        this.#hotspot.style.height = `calc(${window.getComputedStyle(this.#wrapper).fontSize}*1.05)`;
        this.#hotspot.style.width = '1ch';
        this.#hotspot.style.opacity = 0;

        this.length = length;
        this.isRunning = this.#options.runAnimation;
    }

    #getRandomChars(charArr, count) {
        const len = charArr.length;
        let retVal = '';
        for (let i = 0; i < count; i++) {
            const idx = Math.floor(Math.random() * len);
            retVal += charArr[idx];
        }
        return retVal;
    }

    #animate = () => {
        if (this.#changeDirection) {
            const newPos = (this.#options.direction === 'crypt' ? '-2ch' : '-1ch');
            this.#options.direction = (this.#options.direction === 'crypt' ? 'decrypt' : 'crypt');
            this.#changeDirection = false;
            this.#textElement.animate([{ left: newPos }], { duration: 100 * this.#options.speedFactor, iterations: 1 }).onfinish = () => { this.#textElement.style.left = newPos; this.#animate(); };
            return;
        }
        if (this.#runAnimation) {
            this.#running = true;
            this.#hotspot.animate([{ opacity: 1 }], { duration: 100 * this.#options.speedFactor, iterations: 1 }).onfinish = this.#evtHotspot1;
        } else {
            this.#running = false;
        }
    }

    #evtHotspot1 = () => {
        this.#hotspot.style.opacity = 1;
        const text = this.#textElement.textContent;
        if (this.#options.direction === 'crypt') {
            this.#textElement.innerHTML = text.slice(0, this.#nbChars) + this.#getRandomChars(this.#digits, 1) + text.slice(this.#nbChars + 1)
        } else {
            this.#textElement.innerHTML = text.slice(0, this.#nbChars + 1) + this.#getRandomChars(this.#chars, 1) + text.slice(this.#nbChars + 2)
        }
        setTimeout(() => this.#hotspot.animate([{ opacity: 0 }], { duration: 200 * this.#options.speedFactor, iterations: 1 }).onfinish = this.#evtHotspot2, 100);
    }

    #evtHotspot2 = () => {
        this.#hotspot.style.opacity=0;
        setTimeout(() => {
            this.#textElement.animate([{ left: this.#options.direction === 'crypt' ? '0ch' : '-3ch' }], { duration: 100 * this.#options.speedFactor, iterations: 1 }).onfinish = this.#evtText;
        }, 100);
    }

    #evtText = () => {
        const text = this.#textElement.textContent;
        if (this.#options.direction === 'crypt') {
            this.#textElement.innerHTML = this.#getRandomChars(this.#chars, 1) + text.slice(0, -1);
        } else {
            this.#textElement.innerHTML = text.slice(1) + this.#getRandomChars(this.#digits, 1);
        }
        setTimeout(() => this.#animate(), 100);
    }

    get length() {
        return this.#nbChars * 2 - 1;
    }

    set length(newValue) {
        if (newValue < 1) {
            console.error('Invalid length: must be >= 1');
        } else {
            this.#nbChars = Math.floor((newValue + 1) / 2);
            this.#hotspot.style.left = `${this.#nbChars - 1}ch`;
            this.#wrapper.style.width = `${this.#nbChars * 2 - 1}ch`;
            this.#textElement.style.width = `${this.#nbChars * 2 + 1}ch`;
            const oldText = this.#textElement.textContent;
            let newText = oldText;
            if (oldText.length === 0) {
                newText = this.#getRandomChars(this.#chars, this.#nbChars + 1) + this.#getRandomChars(this.#digits, this.#nbChars + 1);
            } else {
                const nbCharsDiff = (this.#nbChars * 2 + 1 + 2 ) - (oldText.length);
                if (nbCharsDiff > 0) {
                    // add characters
                    newText = this.#getRandomChars(this.#chars, nbCharsDiff / 2) + oldText + this.#getRandomChars(this.#digits, nbCharsDiff / 2);
                } else if (nbCharsDiff < 0) {
                    // remove characters
                    newText = oldText.slice(-nbCharsDiff / 2, oldText.length + nbCharsDiff + 1)
                }
            }
            this.#textElement.innerHTML = newText;
        }
        return this.length;
    }

    get direction () {
        return this.#options.direction
    }

    set direction (operation) {
        if (['crypt', 'decrypt'].includes(operation)) {
            if (operation !== this.#options.direction) {
                this.#changeDirection = true;
                if (!this.#running) {
                    this.#animate();
                };
            }
        } else {
            console.error(`Invalid direction: ${operation}`);
        }
    }

    get speedFactor() {
        return this.#options.speedFactor;
    }

    set speedFactor(newValue) {
        this.#options.speedFactor = newValue;
        return newValue;
    }

    get isRrunning() {
        return this.#running;
    }

    set isRunning(newValue) {
        this.#runAnimation = newValue;
        if (newValue && !this.#running) {
            this.#animate();
        };
        return newValue;
    }
}
