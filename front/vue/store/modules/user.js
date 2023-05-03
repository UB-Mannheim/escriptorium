import { retrieveGroups } from "../../../src/api";

// initial state
const state = () => ({
    /**
     * groups: [{
     *     pk: Number,
     *     name: String,
     *     owner: Number,
     *     users: Array<{
     *         pk: Number,
     *         username: String,
     *         email: String,
     *         first_name?: String,
     *         last_name?: String,
     *     }>,
     * }],
     */
    groups: [],
});

const getters = {};

const actions = {
    async fetchGroups({ commit }) {
        const { data } = await retrieveGroups();
        if (data?.results) {
            commit("setGroups", data.results);
        }
    },
};

const mutations = {
    setGroups(state, groups) {
        state.groups = groups;
    },
};

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations,
};
