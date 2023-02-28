import "../vue/index.css";
import Vuex from "vuex";
import Vue from "vue";
import store from "../vue/store";
import FloatingVue from "floating-vue";
import "floating-vue/dist/style.css";

Vue.use(Vuex);
Vue.prototype.$store = store;

Vue.use(FloatingVue);

export const parameters = {
    actions: { argTypesRegex: "^on[A-Z].*" },
    controls: {
        matchers: {
            color: /(background|color)$/i,
            date: /Date$/,
        },
    },
    themes: {
        clearable: false,
        default: "Light mode",
        list: [
            { name: "Light mode", class: "light-mode", color: "#D3D3D3" },
            { name: "Dark mode", class: "dark-mode", color: "#696969" },
        ],
    },
};
