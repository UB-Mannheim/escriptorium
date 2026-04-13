import Vue from "vue";
import store from "../store";
import ModelTraining from "../pages/ModelTraining/ModelTraining.vue";

export default new Vue({
    el: "#model-training",
    store,
    components: {
        "model-training": ModelTraining,
    },
});
