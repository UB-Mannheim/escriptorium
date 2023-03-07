import Vue from "vue";
import Vuex, { Store } from "vuex";
import FloatingVue from "floating-vue";
import alerts from "./modules/alerts";
import filter from "./modules/filter";
import ontology from "./modules/ontology";
import project from "./modules/project";
import projects from "./modules/projects";
import "floating-vue/dist/style.css";

Vue.use(Vuex);

Vue.use(FloatingVue);

export default new Store({
    strict: process.env.NODE_ENV !== "production",
    modules: {
        alerts,
        filter,
        ontology,
        project,
        projects,
    },
});
