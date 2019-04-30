var userProfile;

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

    get(key) {
        return this.settings[key];
    }
}

$(document).ready(function() {
    userProfile = new Profile();
});
