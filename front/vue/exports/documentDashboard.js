import Vue from "vue";
import store from "../store";
import Document from "../pages/Document/Document.vue";

export default new Vue({
    el: "#document-dashboard",
    store,
    components: {
        "document-dashboard": Document,
    },
});
