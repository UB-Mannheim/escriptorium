import Vue from "vue";
import store, { gettextReady } from "../store";
import Images from "../pages/Images/Images.vue";

gettextReady.then(() =>
    new Vue({
        el: "#images-page",
        store,
        components: {
            "images-page": Images,
        },
    })
);
