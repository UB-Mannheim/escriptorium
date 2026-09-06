import Vue from "vue";
import store, { gettextReady } from "../store";
import ProjectsList from "../pages/ProjectsList/ProjectsList.vue";

gettextReady.then(() =>
    new Vue({
        el: "#projects-list",
        store,
        components: {
            "projects-list": ProjectsList,
        },
    })
);
