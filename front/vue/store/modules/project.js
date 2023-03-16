import axios from "axios";
import {
    retrieveProject,
    retrieveProjectCharacters,
    retrieveProjectDocuments,
    retrieveProjectDocumentTags,
    retrieveProjectOntology,
} from "../../../src/api";
import { tagColorToVariant } from "../util/color";

// initial state
const state = () => ({
    /**
     * characters: [{
     *    char: String,
     *    frequency: Number,
     * }]
     */
    characters: [],
    charactersModalOpen: false,
    /**
     * charactersSort: {
     *    direction: Number,
     *    field: String,
     * }
     */
    charactersSort: {
        direction: 1,
        field: "char",
    },
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
     * Change the ontology table category and fetch the selected ontology.
     */
    async changeOntologyCategory({ commit, dispatch }, category) {
        commit("ontology/setCategory", category, { root: true });
        try {
            await dispatch("fetchProjectOntology");
        } catch (error) {
            dispatch("alerts/addError", error, { root: true });
        }
    },
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
        } else {
            throw new Error("Unable to retrieve project");
        }
        commit("setLoading", false);
    },
    /**
     * Fetch the current project.
     */
    async fetchProjectCharacters({ commit, state }) {
        commit("setLoading", true);
        const { data } = await retrieveProjectCharacters({
            projectId: state.id,
            field: state.charactersSort.field,
            direction: state.charactersSort.direction,
        });
        if (data?.results) {
            commit("setCharacters", data.results);
        } else {
            throw new Error("Unable to retrieve characters");
        }
        commit("setLoading", false);
    },
    /**
     * Fetch documents in the current project.
     */
    async fetchProjectDocuments({ commit, state, rootState }) {
        commit("setLoading", true);
        const { data } = await retrieveProjectDocuments({
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
     * Fetch the current project ontology, given this project's id from state, plus
     * ontology category and sorting params from ontology Vuex store.
     */
    async fetchProjectOntology({ commit, state, rootState }) {
        commit("setLoading", true);
        const { data } = await retrieveProjectOntology({
            projectId: state.id,
            category: rootState.ontology.category,
            sortField: rootState.ontology.sortState?.field,
            sortDirection: rootState.ontology.sortState?.direction,
        });
        if (data?.results) {
            commit("ontology/setOntology", data.results, { root: true });
            commit("setLoading", false);
        } else {
            commit("setLoading", false);
            throw new Error(
                `Unable to retrieve ${rootState.ontology.category} ontology`,
            );
        }
    },
    /**
     * Navigate to the images page for this document.
     */
    navigateToImages(_, item) {
        // TODO: implement this; not yet designed
        console.log(item);
    },
    /**
     * Open the "project characters" modal.
     */
    openCharactersModal({ commit }) {
        commit("setCharactersModalOpen", true);
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
     * Open the "project ontology" modal.
     */
    openOntologyModal({ commit }) {
        commit("ontology/setModalOpen", true, { root: true });
    },
    /**
     * Event handler for sorting the project ontology table; sets the sort state on the
     * ontology Vuex store, then makes a call to fetch project ontology based on current state.
     */
    async sortOntology({ commit, dispatch }, { field, direction }) {
        commit("ontology/setSortState", { field, direction }, { root: true });
        try {
            await dispatch("fetchProjectOntology");
        } catch (error) {
            dispatch("alerts/addError", error, { root: true });
        }
    },
    /**
     * Set the default transcription level on one of the documents in the list, then
     * fetch the documents list again with updated data.
     *
     * TODO: figure out implementation.
     */
    // async setDocDefaultTranscription({ commit, dispatch }, documentPk, level) {
    //     commit("setLoading", true);
    //     try {
    //         await updateDocument(documentPk, {
    //             default_transcription_level: level,
    //         });
    //         await dispatch("fetchProjectDocuments");
    //     } catch (error) {
    //         commit("setLoading", false);
    //         dispatch("alerts/addError", error, { root: true });
    //     }
    // },
    /**
     * Set the ID of the project on the state (happens immediately on page load).
     */
    setId({ commit }, id) {
        commit("setId", id);
    },
    /**
     * Change the characters sort field and perform another fetch for characters.
     */
    async sortCharacters({ commit, dispatch }, field) {
        let direction = 1;
        if (field === "frequency") {
            direction = -1;
        }
        commit("setCharactersSort", { field, direction });
        try {
            await dispatch("fetchProjectCharacters");
        } catch (error) {
            dispatch("alerts/addError", error, { root: true });
        }
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
    setCharacters(state, characters) {
        state.characters = characters;
    },
    setCharactersModalOpen(state, open) {
        state.charactersModalOpen = open;
    },
    setCharactersSort(state, sortState) {
        state.charactersSort = sortState;
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
