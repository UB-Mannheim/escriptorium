import Vue from "vue";
import store from "../store";
import ProjectsList from "../pages/ProjectsList/ProjectsList.vue";

export default new Vue({
    el: "#projects-list",
    store,
    components: {
        "projects-list": ProjectsList,
    },
});
