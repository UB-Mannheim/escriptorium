import { assign } from "lodash";

export const initialState = () => ({
    all: [],
});

export const mutations = {
    set(state, taxonomies) {
        state.all = taxonomies;
    },
    reset(state) {
        assign(state, initialState());
    },
};

export const actions = {};

export default {
    namespaced: true,
    state: initialState(),
    mutations,
    actions,
};
