import Vue from "vue";
import Vuex, { Store } from "vuex";
import filter from "./modules/filter";

Vue.use(Vuex);

export default new Store({
    modules: {
        filter,
    },
});
