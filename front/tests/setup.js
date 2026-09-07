import Vue from "vue/dist/vue";
import Vuex from "vuex";

// Vue is used as a global in many components (Vue.extend, Vue.nextTick, etc.)
global.Vue = Vue;
Vue.use(Vuex);

// jsdom does not set document.currentScript (it stays null), but
// scriptname.js reads it at module load time. Stub it so modules importing
// SCRIPT_NAME can be loaded in tests.
Object.defineProperty(document, "currentScript", {
    configurable: true,
    get: () => ({ src: "" }),
});
