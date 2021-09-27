class Profile {
    constructor() {
        let profile = window.localStorage.getItem('escriptorium.userProfile');
        if (profile) {
            this.settings = JSON.parse(profile).settings;
        } else {
            this.settings = {};
        }
    }

    saveProfile() {
        window.localStorage.setItem('escriptorium.userProfile', JSON.stringify({
            'settings': this.settings
        }));
    }

    set(key, value) {
        this.settings[key] = value;
        this.saveProfile();
    }

    get(key, default_) {
        return this.settings[key] || default_;
    }

    delete(key) {
        delete this.settings[key];
        this.saveProfile();
    }

    getCookieConsent() {
        // get cookie consent.
        if (!this.get('cookie-consent')) {
            let alert = Alert.add('cookie-consent',
                                  "eScriptorium uses cookies to store the user session and local storage to save user interface preferences.",
                                  "warning",
                                  [{src: '', text:'Accept', cssClass: 'btn btn-outline-dark btn-sm mt-2'}]);
            alert.htmlElement.querySelector('.additional a').addEventListener('click', function(ev) {
                this.set('cookie-consent', true);
                return false;
            }.bind(this));
        }
    }
}

export var userProfile = new Profile();
