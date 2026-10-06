import Vue from "vue";
import store, { gettextReady } from "./index.js";
import Editor from "../../vue/components/Editor.vue";

export var partVM;

// Mount after the gettext plugin is installed (see gettextReady), like the
// other page entries do; otherwise the first render would call $gettext
// before it exists.
gettextReady.then(() =>
    (partVM = new Vue({
        el: "#editor",
        store,
        components: {
            editor: Editor,
        },
    }))
);
