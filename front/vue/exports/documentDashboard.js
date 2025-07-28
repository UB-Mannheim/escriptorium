import Vue from "vue";
import VueI18n from 'vue-i18n';
import store from "../store";
import Document from "../pages/Document/Document.vue";

Vue.use(VueI18n);

export default new Vue({
    el: "#document-dashboard",
    store,
    components: {
        "document-dashboard": Document,
    },
});
