import axios from "axios";
import {
    retrieveCurrentUser,
    retrieveGroups,
    retrieveModels,
} from "../../../src/api";

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
        let models = [];
        const { data } = await retrieveModels("segment");
        if (!data?.results) throw new Error("Unable to retrieve segmentation models");
        models = data.results;
        let nextPage = data.next;
        while (nextPage) {
            const res = await axios.get(nextPage);
            nextPage = res.data.next;
            models = [...models, ...res.data.results];
        }
        commit("setSegmentationModels", models);
    },
    /**
     * Fetch recognition models the user has access to.
     */
    async fetchRecognizeModels({ commit }) {
        let models = [];
        const { data } = await retrieveModels("recognize");
        if (!data?.results) throw new Error("Unable to retrieve recognition models");
        models = data.results;
        let nextPage = data.next;
        while (nextPage) {
            const res = await axios.get(nextPage);
            nextPage = res.data.next;
            models = [...models, ...res.data.results];
        }
        commit("setRecognitionModels", models);
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
