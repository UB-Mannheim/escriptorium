import Vue from "vue";
import store from "../store";
import Project from "../pages/Project/Project.vue";

export default new Vue({
    el: "#project-dashboard",
    store,
    components: {
        "project-dashboard": Project,
    },
});
