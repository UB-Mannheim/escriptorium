// Per-language translation catalogs loaded at runtime.
//
// Each JSON file is produced by `gettext-compile` from the corresponding
// .po file (see package.json `gettext:compile`). `gettext-compile` wraps
// its output in a top-level key derived from the PO `Language:` header
// (e.g. `{ "de": { "msgid": "translation", ... } }`). We unwrap that
// single key here so the resulting shape matches what `vue-gettext`
// expects (`{ de: { ... } }`).

import enRaw from "./en.json";
import frRaw from "./fr.json";
import deRaw from "./de.json";

function unwrap(raw) {
    // `en.json` may legitimately be an empty object during early
    // bootstrapping; in that case there's no key to unwrap.
    if (!raw || typeof raw !== "object") return {};
    const keys = Object.keys(raw);
    if (keys.length === 1) return raw[keys[0]];
    return raw;
}

const catalogs = {
    en: unwrap(enRaw),
    fr: unwrap(frRaw),
    de: unwrap(deRaw),
};

export default catalogs;
