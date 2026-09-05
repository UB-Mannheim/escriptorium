// Central runtime translation support for the eScriptorium frontend.
//
// We use vue-gettext to translate strings in the Vue application at runtime
// and `easygettext` (CLI tool) to extract strings from .vue/.js sources
// into a .pot template (see `npm run gettext:extract`).
//
// Workflow:
//   1. Developers add `v-translate` directives in templates and
//      `this.$gettext("…")` calls in scripts.
//   2. `npm run gettext:extract` regenerates `src/translations/template.pot`.
//   3. Translators fill the .po file (per language) using a tool like Poedit
//      or `msgmerge` + manual editing.
//   4. `gettext-compile` converts each .po into a JSON catalog (see
//      `npm run gettext:compile`).
//   5. The catalogs are required from `./catalogs.js` and loaded by
//      `installGettext` below at runtime.

import Vue from "vue";
import Gettext from "vue-gettext";
import catalogs from "./catalogs.js";

export const DEFAULT_LANGUAGE = "en";

export const availableLanguages = {
    en: "English",
    fr: "Français",
    de: "Deutsch",
    es: "Español",
};

function readInitialLanguage() {
    // 1. User's previous choice (localStorage).
    try {
        const stored = window.localStorage.getItem("escriptorium-language");
        if (stored && catalogs[stored]) return stored;
    } catch (_) {
        // localStorage may be unavailable (e.g. private mode).
    }
    // 2. <html lang="…"> rendered by Django (see app/escriptorium/templates/base.html).
    const htmlLang = (document.documentElement.lang || "").split("-")[0];
    if (htmlLang && catalogs[htmlLang]) return htmlLang;
    return DEFAULT_LANGUAGE;
}

export function installGettext(store) {
    const language = readInitialLanguage();
    Vue.use(Gettext, {
        availableLanguages,
        defaultLanguage: DEFAULT_LANGUAGE,
        translations: catalogs,
        silent: true, // don't spam console with missing-translation warnings
    });
    // The plugin has no option for the initial language; it always starts on
    // defaultLanguage. Override it right after installation.
    Vue.config.language = language;

    // Seed the locale store with the active language. The store may
    // be omitted (e.g. on pages that don't use the locale module).
    if (store && store.commit) {
        store.commit("locale/SET_LANGUAGE", language);
    }

    return language;
}

// Change the active UI language at runtime. vue-gettext keeps the active
// language on Vue.config.language and re-renders every component that
// uses $gettext / v-translate when that value changes.
export function setLanguage(code) {
    if (!catalogs[code]) {
        // Unknown language – fall back to the default. The English strings
        // embedded in the source serve as msgids in this case.
        code = DEFAULT_LANGUAGE;
    }
    try {
        window.localStorage.setItem("escriptorium-language", code);
    } catch (_) {
        // localStorage may be unavailable.
    }
    Vue.config.language = code;
}
