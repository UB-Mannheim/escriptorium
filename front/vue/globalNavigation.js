import Vue from "vue";
import store from "./store";
import GlobalNavigation from "../vue/components/GlobalNavigation/GlobalNavigation.vue";
import "../vue/index.css";

export default new Vue({
    el: "#vue-global-nav",
    store,
    components: {
        "global-navigation": GlobalNavigation,
    },
});
