import Vue from "vue";
import store from "../store";
import Images from "../pages/Images/Images.vue";

export default new Vue({
    el: "#images-page",
    store,
    components: {
        "images-page": Images,
    },
});
