import Vue from "vue";
import store from "../store";
import OntologyOverview from "../pages/OntologyOverview/OntologyOverview.vue";

export default new Vue({
    el: "#ontology-overview-page",
    store,
    components: {
        "ontology-overview-page": OntologyOverview,
    },
});
