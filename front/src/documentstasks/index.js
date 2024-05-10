import Vue from "vue";
import Vuex from "vuex";
import { assign } from "lodash";
import * as api from "./api.js";

Vue.use(Vuex);

const initialState = () => ({
    documentsTasks: {},
});

const mutations = {
    setDocumentsTasks(state, payload) {
        state.documentsTasks = assign({}, state.documentsTasks, payload);
    },
};

const actions = {
    async fetchDocumentsTasks({ commit }, params) {
        try {
            const resp = await api.listDocumentsTasks(params);
            let data = resp.data;
            commit("setDocumentsTasks", data);
        } catch (err) {
            console.log("couldn't fetch documents tasks!", err);
        }
    },

    async cancelDocumentTasks({ commit }, id) {
        try {
            const resp = await api.cancelDocumentTasks(id);
            commit("setDocumentsTasks", {});
            return resp.data;
        } catch (err) {
            console.log(`couldn't cancel tasks for document ${id}!`, err);
            throw err;
        }
    },
};

export default new Vuex.Store({
    state: initialState(),
    mutations,
    actions,
});
