import { retrieveCurrentUser, retrieveGroups } from "../../../src/api";

// initial state
const state = () => ({
    canInvite: false,
    firstName: "",
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
    isStaff: false,
});

const getters = {};

const actions = {
    async fetchCurrentUser({ commit, dispatch }) {
        try {
            const { data } = await retrieveCurrentUser();
            commit("setCanInvite", data.can_invite);
            commit("setIsStaff", data.is_staff);
            commit("setFirstName", data.first_name);
        } catch (error) {
            dispatch("alerts/addError", error, { root: true });
        }
    },
    async fetchGroups({ commit }) {
        const { data } = await retrieveGroups();
        if (data?.results) {
            commit("setGroups", data.results);
        }
    },
};

const mutations = {
    setCanInvite(state, canInvite) {
        state.canInvite = canInvite;
    },
    setFirstName(state, firstName) {
        state.firstName = firstName;
    },
    setGroups(state, groups) {
        state.groups = groups;
    },
    setIsStaff(state, isStaff) {
        state.isStaff = isStaff;
    },
};

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations,
};
