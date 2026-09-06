import Vue from "vue";
import store, { gettextReady } from "../store";
import OntologyOverview from "../pages/OntologyOverview/OntologyOverview.vue";

gettextReady.then(() =>
    new Vue({
        el: "#ontology-overview-page",
        store,
        components: {
            "ontology-overview-page": OntologyOverview,
        },
    })
);
