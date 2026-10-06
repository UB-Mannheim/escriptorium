import Vue from "vue";
import Vuex, { Store } from "vuex";
import vueFilterPrettyBytes from "vue-filter-pretty-bytes";
import document from "./store/document";
import parts from "./store/parts";
import lines from "./store/lines";
import regions from "./store/regions";
import transcriptions from "./store/transcriptions";
import taxonomies from "./store/taxonomies";
import imageAnnotations from "./store/image_annotations";
import textAnnotations from "./store/text_annotations";
import documentslist from "./store/documentslist";
import forms from "../../vue/store/modules/forms";
import alerts from "../../vue/store/modules/alerts";
import globalTools from "./store/globalTools";
import { installGettext } from "../translations/index.js";

Vue.use(Vuex);
Vue.use(vueFilterPrettyBytes);

const store = new Store({
    modules: {
        alerts,
        document,
        parts,
        lines,
        regions,
        transcriptions,
        taxonomies,
        imageAnnotations,
        textAnnotations,
        documentslist,
        globalTools,
        forms,
    },
});

// Install vue-gettext so this entry can use $gettext / v-translate too.
// The initial language's catalog is fetched on demand, so this returns a
// promise: `main.js` must await `gettextReady` before mounting the Vue
// root, otherwise the first render calls $gettext before it exists.
// Null store – this entry's store has no Vuex locale module.
export const gettextReady = installGettext(null);

export default store;
