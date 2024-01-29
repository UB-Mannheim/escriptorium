import axios from "axios";
import {
    createProject,
    createProjectTag,
    deleteProject,
    retrieveAllProjectTags,
    retrieveProjects,
} from "../../../src/api";
import { tagColorToVariant } from "../util/color";

// initial state
const state = () => ({
    createModalOpen: false,
    deleteModalOpen: false,
    loading: true,
    /**
     * If there are additional pages of results, the next one will go here
     */
    nextPage: "",
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
    projectToDelete: {},
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
     *     pk: Number,
     *     variant: Number,
     * }]
     */
    tags: [],
});

const getters = {};

const actions = {
    /**
     * Close the "create project" modal.
     */
    closeCreateModal({ commit }) {
        commit("setCreateModalOpen", false);
    },
    /**
     * Close the "delete project" modal.
     */
    closeDeleteModal({ commit }) {
        commit("setDeleteModalOpen", false);
    },
    /**
     * Create a new project with the project data from state; show error
     * alert on failure.
     */
    async createNewProject({ dispatch, commit, rootState }) {
        commit("setLoading", true);
        try {
            const { data } = await createProject({
                name: rootState.forms?.editProject?.name,
                tags: rootState.forms?.editProject?.tags,
                guidelines: rootState.forms?.editProject?.guidelines,
            });
            if (data) {
                // show toast alert on success
                dispatch(
                    "alerts/add",
                    {
                        color: "success",
                        message: "Project created successfully",
                    },
                    { root: true },
                );
                commit("setCreateModalOpen", false);
                // redirect to project dashboard
                window.location = `/project/${data.slug}`;
            } else {
                commit("setLoading", false);
                throw new Error("Unable to create project");
            }
        } catch (error) {
            commit("setLoading", false);
            dispatch("alerts/addError", error, { root: true });
        }
        commit("setLoading", false);
    },
    /**
     * Create a new tag with the data from state, reload list of tags.
     */
    async createNewProjectTag({ commit, dispatch, rootState, state }, color) {
        commit("setLoading", true);
        try {
            const { data } = await createProjectTag({
                name: rootState?.forms?.editProject?.tagName,
                color,
            });
            if (data?.pk) {
                // set the new data on the state
                const tags = [...state.tags];
                tags.push({ ...data, variant: tagColorToVariant(color) });
                commit("setTags", tags);
                // select the new tag and reset the tag name add/search field
                commit(
                    "forms/addToArray",
                    { form: "editProject", field: "tags", value: data.pk },
                    { root: true },
                );
                commit(
                    "forms/setFieldValue",
                    { form: "editProject", field: "tagName", value: "" },
                    { root: true },
                );
            } else {
                commit("setLoading", false);
                throw new Error("Unable to create tag");
            }
        } catch (error) {
            dispatch("alerts/addError", error, { root: true });
        }
        commit("setLoading", false);
    },
    async deleteProject({ dispatch, commit, state }) {
        commit("setLoading", true);
        try {
            await deleteProject(state.projectToDelete.id);
            // show toast alert on success
            dispatch(
                "alerts/add",
                {
                    color: "success",
                    message: "Project deleted successfully",
                },
                { root: true },
            );
            // fetch projects list again
            await dispatch("fetchProjects");
            commit("setDeleteModalOpen", false);
        } catch (error) {
            commit("setLoading", false);
            dispatch("alerts/addError", error, { root: true });
        }
        commit("setLoading", false);
    },
    /**
     * Fetch the full list of tags across all projects for use in the tag filter.
     */
    async fetchAllProjectTags({ commit }) {
        commit("setLoading", true);
        const { data } = await retrieveAllProjectTags();
        if (data?.results) {
            commit(
                "setTags",
                data.results.map((tag) => ({
                    ...tag,
                    variant: tagColorToVariant(tag.color),
                })),
            );
        } else {
            commit("setLoading", false);
            throw new Error("Unable to retrieve project tags");
        }
        commit("setLoading", false);
    },
    /**
     * Fetch the full list of projects, using currently applied sort and filters
     * from state.
     */
    async fetchProjects({ state, commit, rootState }) {
        commit("setLoading", true);
        const { data } = await retrieveProjects({
            field: state?.sortState?.field,
            direction: state?.sortState?.direction,
            filters: rootState?.filter?.filters,
        });
        if (data?.results) {
            commit(
                "setProjects",
                data.results.map((result) => ({
                    ...result,
                    tags: { tags: result.tags },
                    // link to project dashboard
                    href: `/project/${result.slug}/`,
                })),
            );
            commit("setNextPage", data.next);
        } else {
            commit("setLoading", false);
            throw new Error("Unable to retrieve projects");
        }
        commit("setLoading", false);
    },
    /**
     * Fetch the next page of projects, retrieved from fetchProjects, and add
     * all of its projects on the state.
     */
    async fetchNextPage({ state, commit, dispatch }) {
        commit("setLoading", true);
        try {
            const { data } = await axios.get(state.nextPage);
            if (data?.results) {
                data.results.forEach((result) => {
                    commit("addProject", {
                        ...result,
                        tags: { tags: result.tags },
                        // link to project dashboard
                        href: `/project/${result.slug}/`,
                    });
                });
                commit("setNextPage", data.next);
            } else {
                commit("setLoading", false);
                throw new Error("Unable to retrieve projects");
            }
        } catch (error) {
            commit("setLoading", false);
            dispatch("alerts/addError", error, { root: true });
        }
        commit("setLoading", false);
    },
    /**
     * Open the "create project" modal and clear the new project name, if there is one.
     */
    openCreateModal({ commit, dispatch }) {
        dispatch("forms/clearForm", "editProject", { root: true });
        commit("setCreateModalOpen", true);
    },
    /**
     * Open the "delete project" modal.
     */
    openDeleteModal({ commit }, project) {
        commit("setProjectToDelete", project);
        commit("setDeleteModalOpen", true);
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
            commit("setLoading", false);
            dispatch("alerts/addError", error, { root: true });
        }
    },
};

const mutations = {
    addProject(state, project) {
        state.projects.push(project);
    },
    setProjects(state, projects) {
        state.projects = projects;
    },
    setCreateModalOpen(state, open) {
        state.createModalOpen = open;
    },
    setDeleteModalOpen(state, open) {
        state.deleteModalOpen = open;
    },
    setLoading(state, loading) {
        state.loading = loading;
    },
    setNewProjectName(state, input) {
        state.newProjectName = input;
    },
    setNextPage(state, nextPage) {
        state.nextPage = nextPage;
    },
    setProjectToDelete(state, project) {
        state.projectToDelete = project;
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
