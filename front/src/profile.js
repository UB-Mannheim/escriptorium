class Profile {
    constructor() {
        let profile = window.localStorage.getItem("escriptorium.userProfile");
        if (profile) {
            this.settings = JSON.parse(profile).settings;
        } else {
            this.settings = {};
        }
    }

    saveProfile() {
        window.localStorage.setItem(
            "escriptorium.userProfile",
            JSON.stringify({
                settings: this.settings,
            }),
        );
    }

    set(key, value) {
        this.settings[key] = value;
        this.saveProfile();
    }

    get(key, default_) {
        if (this.settings[key] !== undefined) return this.settings[key];
        else return default_;
    }

    delete(key) {
        delete this.settings[key];
        this.saveProfile();
    }

    setUserId(id) {
        this.userId = id;
    }

    getCookieConsent() {
        // get cookie consent.
        if (!this.get("cookie-consent")) {
            const i18n = document.getElementById("cookie-consent-i18n");
            const message =
                i18n?.querySelector(".message")?.textContent.trim() ||
                "eScriptorium uses cookies to store the user session and local storage to save user interface preferences.";
            const accept =
                i18n?.querySelector(".accept")?.textContent.trim() || "Accept";
            let alert = Alert.add(
                "cookie-consent",
                message,
                "warning",
                [
                    {
                        src: "",
                        text: accept,
                        cssClass: "btn btn-outline-dark btn-sm mt-2",
                        targetBlank: false,
                    },
                ],
            );
            alert.htmlElement.querySelector(".additional a").addEventListener(
                "click",
                function (_ev) {
                    this.set("cookie-consent", true);
                    return false;
                }.bind(this),
            );
        }
    }

    resetCookieConsent() {
        // convenience method
        this.set("cookie-consent", false);
    }
}

export var userProfile = new Profile();
