import Vue from "vue/dist/vue";
import Vuex from "vuex";

// Vue is used as a global in many components (Vue.extend, Vue.nextTick, etc.)
global.Vue = Vue;
Vue.use(Vuex);
