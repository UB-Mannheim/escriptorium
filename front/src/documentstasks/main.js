import Vue from "vue";
import store, { gettextReady } from "./index.js";
import DocumentsTasks from "../../vue/components/DocumentsTasks/List.vue";

// Mount after the gettext plugin is installed (see gettextReady), like the
// other page entries do; otherwise the first render would call $gettext
// before it exists.
gettextReady.then(() =>
    new Vue({
        el: "#documents_tasks",
        store,
        components: {
            documentstasks: DocumentsTasks,
        },
    })
);
