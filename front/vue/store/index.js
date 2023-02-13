import Vue from "vue";
import Vuex, { Store } from "vuex";
import alerts from "./modules/alerts";
import filter from "./modules/filter";
import projects from "./modules/projects";

Vue.use(Vuex);

export default new Store({
    strict: process.env.NODE_ENV !== "production",
    modules: {
        alerts,
        filter,
        projects,
    },
});
