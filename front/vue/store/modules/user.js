import { retrieveCurrentUser, retrieveGroups, retrieveModels } from "../../../src/api";

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
    segmentationModels: [],
    recognitionModels: [],
    username: "",
});

const getters = {};

const actions = {
    async fetchCurrentUser({ commit, dispatch }) {
        try {
            const { data } = await retrieveCurrentUser();
            commit("setCanInvite", data.can_invite);
            commit("setIsStaff", data.is_staff);
            commit("setFirstName", data.first_name);
            commit("setUsername", data.username);
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
    /**
     * Fetch segmentation models the user has access to.
     */
    async fetchSegmentModels({ commit }) {
        const { data } = await retrieveModels("segment");
        if (data?.results) {
            commit("setSegmentationModels", data.results);
        } else {
            throw new Error("Unable to retrieve segmentation models");
        }
    },
    /**
     * Fetch recognition models the user has access to.
     */
    async fetchRecognizeModels({ commit }) {
        const { data } = await retrieveModels("recognize");
        if (data?.results) {
            commit("setRecognitionModels", data.results);
        } else {
            throw new Error("Unable to retrieve recognition models");
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
    setRecognitionModels(state, models) {
        state.recognitionModels = models;
    },
    setSegmentationModels(state, models) {
        state.segmentationModels = models;
    },
    setUsername(state, username) {
        state.username = username;
    },
};

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations,
};
