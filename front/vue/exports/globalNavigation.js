import Vue from "vue";
import store, { gettextReady } from "../store";
import GlobalNavigation from "../components/GlobalNavigation/GlobalNavigation.vue";
import "../index.css";

gettextReady.then(() =>
    new Vue({
        el: "#vue-global-nav",
        store,
        components: {
            "global-navigation": GlobalNavigation,
        },
    })
);
