import {
    createProject,
    retrieveAllProjectTags,
    retrieveProjects,
} from "../../../src/api";

// initial state
const state = () => ({
    createModalOpen: false,
    newProjectName: "",
    /**
     * projects: [{
     *     name: String,
     *     slug: String,
     *     tags: Array<Object>,
     *     documents_count: Number,
     *     owner: Object,
     *     updated_at: Date,
     *     created_at: Date,
     * }]
     */
    projects: [],
    sortState: {},
    tags: [],
});

const getters = {};

const actions = {
    async createNewProject({ commit, state }) {
        try {
            const { data } = await createProject(state.newProjectName);
            if (data?.projects) {
                commit("setProjects", data.projects);
                // TODO: Show success dialog
                commit("setCreateModalOpen", false);
            } else {
                throw new Error("Unable to create project");
            }
        } catch (error) {
            // TODO: Error handling on frontend
            console.log(error);
        }
    },
    closeCreateModal({ commit }) {
        commit("setCreateModalOpen", false);
    },
    async fetchAllProjectTags({ commit }) {
        try {
            const { data } = await retrieveAllProjectTags();
            if (data?.tags) {
                commit("setTags", data.tags);
            } else {
                throw new Error("Unable to retrieve project tags");
            }
        } catch (error) {
            // TODO: Error handling on frontend
            console.log(error);
        }
    },
    async fetchProjects({ state, commit, rootState }) {
        try {
            const { data } = await retrieveProjects({
                field: state?.sortState?.field,
                direction: state?.sortState?.direction,
                filters: rootState?.filter?.filters,
            });
            if (data?.projects) {
                commit("setProjects", data.projects);
            } else {
                throw new Error("Unable to retrieve projects");
            }
        } catch (error) {
            // TODO: Error handling on frontend
            console.log(error);
        }
    },
    handleNewProjectNameInput({ commit }, input) {
        commit("setNewProjectName", input);
    },
    openCreateModal({ commit }) {
        commit("setNewProjectName", "");
        commit("setCreateModalOpen", true);
    },
    async sortProjects({ commit, dispatch }, { field, direction }) {
        await commit("setSortState", { field, direction });
        await dispatch("fetchProjects");
    },
};

const mutations = {
    setProjects(state, projects) {
        state.projects = projects;
    },
    setCreateModalOpen(state, open) {
        state.createModalOpen = open;
    },
    setNewProjectName(state, input) {
        state.newProjectName = input;
    },
    setTags(state, tags) {
        state.tags = tags;
    },
    setSortState(state, sortState) {
        state.sortState = sortState;
    },
};

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations,
};
