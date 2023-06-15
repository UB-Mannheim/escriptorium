import "../vue/index.css";
import Vuex from "vuex";
import Vue from "vue";
import store from "../vue/store";
import FloatingVue from "floating-vue";
import "floating-vue/dist/style.css";

Vue.use(Vuex);
Vue.prototype.$store = store;

Vue.use(FloatingVue, {
    themes: {
        "escr-tooltip": {
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

export const parameters = {
    actions: { argTypesRegex: "^on[A-Z].*" },
    controls: {
        matchers: {
            color: /(background|color)$/i,
            date: /Date$/,
        },
    },
};
