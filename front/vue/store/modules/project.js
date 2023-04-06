import axios from "axios";
import {
    retrieveDocumentsList,
    retrieveProject,
    retrieveProjectDocumentTags,
} from "../../../src/api";
import { tagColorToVariant } from "../util/color";

// initial state
const state = () => ({
    /**
     * documents: [{
     *     pk: Number,
     *     name: String,
     *     parts_count: Number,
     *     tags: Array<Number>,
     *     transcriptions: Array<{
     *        pk: Number,
     *        name: String,
     *        archived: Boolean,
     *        avg_confidence: Number,
     *     }>,
     *     default_transcription: Number,
     *     updated_at: String,
     *     created_at: String,
     * }]
     */
    documents: [],
    /**
     * documentTags: [{
     *     name: String,
     *     pk: Number,
     *     variant: Number,
     * }]
     */
    documentTags: [],
    editModalOpen: false,
    guidelines: "",
    id: null,
    loading: false,
    name: "",
    nextPage: "",
    /**
     * sharedWithGroups: [{
     *     pk: Number,
     *     name: String,
     * }]
     */
    sharedWithGroups: [],
    /**
     * sharedWithUsers: [{
     *     pk: Number,
     *     first_name?: String,
     *     last_name?: String,
     *     username: String,
     * }]
     */
    sharedWithUsers: [],
    shareModalOpen: false,
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
     * Close the "edit project" modal.
     */
    closeEditModal({ commit }) {
        commit("setEditModalOpen", false);
    },
    /**
     * Fetch the next page of documents, retrieved from fetchProjects, and add
     * all of its projects on the state.
     */
    async fetchNextPage({ state, commit, dispatch }) {
        commit("setLoading", true);
        try {
            const { data } = await axios.get(state.nextPage);
            if (data?.results) {
                data.results.forEach((document) => {
                    commit("addDocument", document);
                });
                commit("setNextPage", data.next);
            } else {
                commit("setLoading", false);
                throw new Error("Unable to retrieve projects");
            }
        } catch (error) {
            dispatch("alerts/addError", error, { root: true });
        }
        commit("setLoading", false);
    },
    /**
     * Fetch the current project.
     */
    async fetchProject({ commit, state }) {
        commit("setLoading", true);
        const { data } = await retrieveProject(state.id);
        if (data) {
            commit("setName", data.name);
            commit(
                "setTags",
                data.tags?.map((tag) => ({
                    ...tag,
                    variant: tagColorToVariant(tag.color),
                })),
            );
            commit("setSharedWithGroups", data.shared_with_groups);
            commit("setSharedWithUsers", data.shared_with_users);
        } else {
            throw new Error("Unable to retrieve project");
        }
        commit("setLoading", false);
    },
    /**
     * Fetch documents in the current project.
     */
    async fetchProjectDocuments({ commit, state, rootState }) {
        commit("setLoading", true);
        const { data } = await retrieveDocumentsList({
            projectId: state.id,
            filters: rootState?.filter?.filters,
            ...state.sortState,
        });
        if (data?.next) {
            commit("setNextPage", data.next);
        }
        if (data?.results) {
            commit(
                "setDocuments",
                data.results.map((result) => ({
                    ...result,
                    tags: { tags: result.tags },
                })),
            );
        } else {
            throw new Error("Unable to retrieve documents");
        }
        commit("setLoading", false);
    },
    /**
     * Fetch all unique tags on documents in the current project.
     */
    async fetchProjectDocumentTags({ commit, state }) {
        commit("setLoading", true);
        const { data } = await retrieveProjectDocumentTags(state.id);
        if (data?.results) {
            commit(
                "setDocumentTags",
                data.results.map((tag) => ({
                    ...tag,
                    variant: tagColorToVariant(tag.color),
                })),
            );
        } else {
            throw new Error("Unable to retrieve document tags");
        }
        commit("setLoading", false);
    },
    /**
     * Navigate to the images page for this document.
     */
    navigateToImages(_, item) {
        // TODO: implement this; not yet designed
        console.log(item);
    },
    /**
     * Open the "create document" modal.
     */
    openCreateModal() {
        // TODO: implement this; not yet designed
    },
    /**
     * Open the "delete document" modal.
     */
    openDeleteModal(_, item) {
        // TODO: implement this; not yet designed
        console.log(item);
    },
    /**
     * Open the "edit project" modal.
     */
    openEditModal({ commit }) {
        commit("setEditModalOpen", true);
    },
    /**
     * Open the "add group or user" modal.
     */
    openShareModal({ commit }) {
        commit("setShareModalOpen", true);
    },
    /**
     * Set the ID of the project on the state (happens immediately on page load).
     */
    setId({ commit }, id) {
        commit("setId", id);
    },
    /**
     * Change the documents list sort and perform another fetch for documents.
     */
    async sortDocuments({ commit, dispatch }, { field, direction }) {
        await commit("setSortState", { field, direction });
        try {
            await dispatch("fetchProjectDocuments");
        } catch (error) {
            dispatch("alerts/addError", error, { root: true });
        }
    },
};

const mutations = {
    addDocument(state, document) {
        state.documents.push(document);
    },
    setDocuments(state, documents) {
        state.documents = documents;
    },
    setDocumentTags(state, tags) {
        state.documentTags = tags;
    },
    setEditModalOpen(state, open) {
        state.editModalOpen = open;
    },
    setId(state, id) {
        state.id = id;
    },
    setLoading(state, loading) {
        state.loading = loading;
    },
    setName(state, name) {
        state.name = name;
    },
    setNextPage(state, nextPage) {
        state.nextPage = nextPage;
    },
    setSharedWithGroups(state, groups) {
        state.sharedWithGroups = groups;
    },
    setSharedWithUsers(state, users) {
        state.sharedWithUsers = users;
    },
    setShareModalOpen(state, open) {
        state.shareModalOpen = open;
    },
    setSortState(state, sortState) {
        state.sortState = sortState;
    },
    setTags(state, tags) {
        state.tags = tags;
    },
};

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations,
};
