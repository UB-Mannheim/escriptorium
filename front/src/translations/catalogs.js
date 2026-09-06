// Per-language translation catalogs, loaded on demand at runtime.
//
// Each JSON file is produced by `gettext-compile` from the corresponding
// .po file (see `gettext:compile` in package.json). `gettext-compile`
// wraps its output in a top-level key derived from the PO `Language:`
// header (e.g. `{ "de": { "msgid": "translation", ... } }`); we unwrap
// that single key so the resulting shape matches what `vue-gettext`
// expects (`{ de: { ... } }`).
//
// Each language is its own webpack chunk (see the webpackChunkName
// comments), so a catalog is only downloaded when that language is
// actually used instead of being shipped with every page load.

// Add a new language here (and its .json file next to this module).
// English needs no catalog: the source strings are English, so there is
// nothing to translate.
const loaders = {
    de: () =>
        import(/* webpackChunkName: "locale-de" */ "./de.json"),
    es: () =>
        import(/* webpackChunkName: "locale-es" */ "./es.json"),
    fr: () =>
        import(/* webpackChunkName: "locale-fr" */ "./fr.json"),
    he: () =>
        import(/* webpackChunkName: "locale-he" */ "./he.json"),
};

const loaded = {};
const pending = {};

function unwrap(raw) {
    if (!raw || typeof raw !== "object") return {};
    const keys = Object.keys(raw);
    if (keys.length === 1) return raw[keys[0]];
    return raw;
}

export function hasCatalog(code) {
    return code === "en" || code in loaders;
}

export function loadCatalog(code) {
    if (code === "en" || !hasCatalog(code)) {
        return Promise.resolve({});
    }
    if (loaded[code]) {
        return Promise.resolve(loaded[code]);
    }
    if (!pending[code]) {
        pending[code] = loaders[code]().then(
            (module) => {
                delete pending[code];
                loaded[code] = unwrap(module.default || module);
                return loaded[code];
            },
            (error) => {
                delete pending[code];
                throw error;
            }
        );
    }
    return pending[code];
}
