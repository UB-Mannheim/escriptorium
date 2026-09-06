import Vue from "vue";
import store, { gettextReady } from "../store";
import Document from "../pages/Document/Document.vue";

gettextReady.then(() =>
    new Vue({
        el: "#document-dashboard",
        store,
        components: {
            "document-dashboard": Document,
        },
    })
);
