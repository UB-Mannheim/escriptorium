import Vue from "vue";
import Vuex, { Store } from "vuex";
import FloatingVue from "floating-vue";
import alerts from "./modules/alerts";
import characters from "./modules/characters";
import filter from "./modules/filter";
import ontology from "./modules/ontology";
import project from "./modules/project";
import projects from "./modules/projects";
import sidebar from "./modules/sidebar";
import "floating-vue/dist/style.css";

Vue.use(Vuex);

Vue.use(FloatingVue, {
    themes: {
        "tags-dropdown": {
            $extend: "dropdown",
        },
    },
});

export default new Store({
    strict: process.env.NODE_ENV !== "production",
    modules: {
        alerts,
        characters,
        filter,
        ontology,
        project,
        projects,
        sidebar,
    },
});
