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
    /**
     * sortState: {
     *     direction: Number,
     *     field: String,
     * }
     */
    sortState: {},
    /**
     * tags: [{
     *     name: String,
     *     variant: Number,
     * }]
     */
    tags: [],
});

const getters = {};

const actions = {
    /**
     * Create a new project with the project name from state; show error
     * alert on failure.
     */
    async createNewProject({ dispatch, commit, state }) {
        try {
            const { data } = await createProject(state.newProjectName);
            if (data?.projects) {
                // show toast alert on success
                dispatch(
                    "alerts/add",
                    {
                        color: "success",
                        message: "Project created successfully",
                    },
                    { root: true },
                );
                // TODO: redirect to the new project
                commit("setProjects", data.projects);
                commit("setCreateModalOpen", false);
            } else {
                throw new Error("Unable to create project");
            }
        } catch (error) {
            dispatch(
                "alerts/add",
                { color: "alert", message: error.message },
                { root: true },
            );
            console.error(error);
        }
    },
    /**
     * Close the "create project" modal.
     */
    closeCreateModal({ commit }) {
        commit("setCreateModalOpen", false);
    },
    /**
     * Fetch the full list of tags across all projects for use in the tag filter.
     */
    async fetchAllProjectTags({ commit }) {
        const { data } = await retrieveAllProjectTags();
        if (data?.tags) {
            commit("setTags", data.tags);
        } else {
            throw new Error("Unable to retrieve project tags");
        }
    },
    /**
     * Fetch the full list of projects, using currently applied sort and filters
     * from state.
     */
    async fetchProjects({ state, commit, rootState }) {
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
    },
    /**
     * Set the new project name on the state.
     */
    handleNewProjectNameInput({ commit }, input) {
        commit("setNewProjectName", input);
    },
    /**
     * Open the "create project" modal and clear the new project name, if there is one.
     */
    openCreateModal({ commit }) {
        commit("setNewProjectName", "");
        commit("setCreateModalOpen", true);
    },
    /**
     * Set the sort state, then attempt to fetch projects with the sort applied, or
     * show an error toast on failure.
     */
    async sortProjects({ commit, dispatch }, { field, direction }) {
        await commit("setSortState", { field, direction });
        try {
            await dispatch("fetchProjects");
        } catch (error) {
            dispatch(
                "alerts/add",
                { color: "alert", message: error.message },
                { root: true },
            );
            console.error(error);
        }
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
