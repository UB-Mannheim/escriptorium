import Vue from "vue";
import store, { gettextReady } from "../store";
import ModelTraining from "../pages/ModelTraining/ModelTraining.vue";

gettextReady.then(() =>
    new Vue({
        el: "#model-training",
        store,
        components: {
            "model-training": ModelTraining,
        },
    })
);
