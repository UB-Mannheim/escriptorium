import Vue from "vue";
import Vuex, { Store } from "vuex";
import FloatingVue from "floating-vue";
import alerts from "./modules/alerts";
import characters from "./modules/characters";
import document from "./modules/document";
import filter from "./modules/filter";
import forms from "./modules/forms";
import images from "./modules/images";
import ontology from "./modules/ontology";
import project from "./modules/project";
import projects from "./modules/projects";
import sidebar from "./modules/sidebar";
import tasks from "./modules/tasks";
import transcription from "./modules/transcription";
import user from "./modules/user";
import "floating-vue/dist/style.css";

Vue.use(Vuex);

Vue.use(FloatingVue, {
    themes: {
        "escr-tooltip": {
            $extend: "dropdown",
        },
        "escr-tooltip-small": {
            $extend: "dropdown",
        },
        "tags-dropdown": {
            $extend: "dropdown",
        },
        "vertical-menu": {
            $extend: "menu",
        },
    },
});

const store = new Store({
    strict: process.env.NODE_ENV !== "production",
    mutations: {
        // update last dispatched action
        // (from https://upstatement.com/blog/last-vuex-action-hero/)
        LAST_DISPATCHED_ACTION: (state, actionObject) => {
            state.lastDispatchedAction = actionObject;
        },
    },
    modules: {
        alerts,
        characters,
        document,
        filter,
        forms,
        images,
        ontology,
        project,
        projects,
        sidebar,
        tasks,
        transcription,
        user,
    },
});

// keep track of last dispatched action (from https://upstatement.com/blog/last-vuex-action-hero/)
// Store the initial instance of the store's dispatch function
const initialDispatch = store.dispatch;

// overwrite `dispatch` on store so that it additionally tracks
// which function was called last
// this is used so we can retry any given function if auth has expired
Object.defineProperty(store, "dispatch", {
    value(name, payload) {
        store.commit("LAST_DISPATCHED_ACTION", { name, payload });
        return initialDispatch(...arguments);
    },
});

export default store;
