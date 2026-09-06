import Vue from "vue";
import store, { gettextReady } from "../store";
import Project from "../pages/Project/Project.vue";

gettextReady.then(() =>
    new Vue({
        el: "#project-dashboard",
        store,
        components: {
            "project-dashboard": Project,
        },
    })
);
