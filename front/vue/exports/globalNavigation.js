import Vue from "vue";
import store from "../store";
import GlobalNavigation from "../components/GlobalNavigation/GlobalNavigation.vue";
import "../index.css";

export default new Vue({
    el: "#vue-global-nav",
    store,
    components: {
        "global-navigation": GlobalNavigation,
    },
});
