import axios from "axios";
import {
    createDocument,
    createProjectDocumentTag,
    editProject,
    retrieveDocumentsList,
    retrieveProject,
    retrieveProjectDocumentTags,
    retrieveScripts,
    shareProject,
} from "../../../src/api";
import { tagColorToVariant } from "../util/color";

// initial state
const state = () => ({
    createDocumentModalOpen: false,
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
    deleteModalOpen: false,
    deleteDocumentModalOpen: false,
    editModalOpen: false,
    guidelines: "",
    id: null,
    loading: false,
    menuOpen: false,
    name: "",
    nextPage: "",
    /**
     * scripts: Array<String>
     */
    scripts: [],
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
     *     email: String,
     *     first_name?: String,
     *     last_name?: String,
     *     username: String,
     * }]
     */
    sharedWithUsers: [],
    shareModalOpen: false,
    slug: "",
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
     * Close the "create document" modal.
     */
    closeCreateDocumentModal({ commit }) {
        commit("setCreateDocumentModalOpen", false);
    },
    /**
     * Close the "edit project" modal and clear out state.
     */
    closeEditModal({ commit, state }) {
        commit("setEditModalOpen", false);
        commit(
            "forms/setFormState",
            {
                form: "editProject",
                formState: {
                    name: state.name,
                    guidelines: state.guidelines,
                    tags: state.tags.map((tag) => tag.pk),
                    tagName: "",
                },
            },
            { root: true },
        );
    },
    /**
     * Close the "delete project" modal.
     */
    closeDeleteModal({ commit }) {
        commit("setDeleteModalOpen", false);
    },
    /**
     * Close the "edit/delete project" menu.
     */
    closeProjectMenu({ commit }) {
        commit("setMenuOpen", false);
    },
    /**
     * Close the "add group or user" modal.
     */
    closeShareModal({ commit }) {
        commit("setShareModalOpen", false);
    },
    /**
     * Create a new document with the data from state.
     */
    async createNewDocument({ commit, dispatch, state, rootState }) {
        commit("setLoading", true);
        try {
            const { data } = await createDocument({
                name: rootState.forms?.editDocument?.name,
                project: state.slug,
                mainScript: rootState.forms?.editDocument?.mainScript,
                readDirection: rootState.forms?.editDocument?.readDirection,
                linePosition: rootState.forms?.editDocument?.linePosition,
                tags: rootState.forms?.editDocument?.tags,
            });
            if (data) {
                // show toast alert on success
                dispatch(
                    "alerts/add",
                    {
                        color: "success",
                        message: "Document created successfully",
                    },
                    { root: true },
                );
                // TODO: redirect to new document
                commit("setCreateDocumentModalOpen", false);
            } else {
                commit("setLoading", false);
                throw new Error("Unable to create document");
            }
        } catch (error) {
            dispatch("alerts/addError", error, { root: true });
        }
        commit("setLoading", false);
    },
    /**
     * Create a new document tag with the data from state.
     */
    async createNewDocumentTag({ commit, dispatch, state, rootState }, color) {
        commit("setLoading", true);
        try {
            const { data } = await createProjectDocumentTag({
                name: rootState?.forms?.editDocument?.tagName,
                color,
                projectId: state.id,
            });
            if (data?.pk) {
                // set the new data on the state
                const documentTags = [...state.documentTags];
                documentTags.push({
                    ...data,
                    variant: tagColorToVariant(color),
                });
                commit("setDocumentTags", documentTags);
                // select the new tag and reset the tag name add/search field
                commit(
                    "forms/selectTag",
                    { form: "editDocument", tag: data },
                    { root: true },
                );
                commit(
                    "forms/setFieldValue",
                    { form: "editDocument", field: "tagName", value: "" },
                    { root: true },
                );
            } else {
                throw new Error("Unable to create tag");
            }
        } catch (error) {
            dispatch("alerts/addError", error, { root: true });
        }
        commit("setLoading", false);
    },
    /**
     * Create a new project tag with the data from state.
     */
    async createNewProjectTag({ commit, dispatch }, color) {
        commit("setLoading", true);
        await dispatch("projects/createNewProjectTag", color, { root: true });
        commit("setLoading", false);
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
    async fetchProject({ commit, dispatch, state, rootState }) {
        // fetch project tags first so we can use it in setTags
        await dispatch(
            { type: "projects/fetchAllProjectTags" },
            { root: true },
        );
        const { data } = await retrieveProject(state.id);
        if (data) {
            commit("setName", data.name);
            commit("setSlug", data.slug);
            commit(
                "setTags",
                rootState.projects.tags.filter((t) => data.tags.includes(t.pk)),
            );
            commit("setSharedWithGroups", data.shared_with_groups);
            commit("setSharedWithUsers", data.shared_with_users);
            commit(
                "forms/setFormState",
                {
                    form: "editProject",
                    formState: {
                        name: data.name,
                        guidelines: data.guidelines,
                        tags: data.tags,
                        tagColor: "",
                        tagName: "",
                    },
                },
                { root: true },
            );
        } else {
            throw new Error("Unable to retrieve project");
        }
        // set off all the other fetches
        await dispatch("fetchProjectDocuments");
        await dispatch("fetchProjectDocumentTags");
        await dispatch("fetchScripts");
    },
    /**
     * Fetch documents in the current project.
     */
    async fetchProjectDocuments({ commit, state, rootState }) {
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
    },
    /**
     * Fetch all unique tags on documents in the current project.
     */
    async fetchProjectDocumentTags({ commit, state }) {
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
    },
    /**
     * Fetch all scripts from the database and set their names on the state.
     */
    async fetchScripts({ commit }) {
        const { data } = await retrieveScripts();
        if (data?.results) {
            commit(
                "setScripts",
                data.results.map((script) => script.name),
            );
        } else {
            throw new Error("Unable to retrieve scripts");
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
     * Open the "create document" modal.
     */
    openCreateDocumentModal({ commit, dispatch }) {
        dispatch("forms/clearForm", "editDocument", { root: true });
        commit("setCreateDocumentModalOpen", true);
    },
    /**
     * Open the "delete project" modal.
     */
    openDeleteModal({ commit }) {
        commit("setDeleteModalOpen", true);
    },
    /**
     * Open the "delete document" modal.
     */
    openDeleteDocumentModal(_, item) {
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
     * Open the "edit/delete project" menu.
     */
    openProjectMenu({ commit }) {
        commit("setMenuOpen", true);
    },
    /**
     * Open the "add group or user" modal.
     */
    openShareModal({ commit }) {
        commit("setShareModalOpen", true);
    },
    async saveProject({ commit, dispatch, state, rootState }) {
        commit("setLoading", true);
        const { name, guidelines, tags } = rootState.forms.editProject;
        try {
            const { data } = await editProject(state.id, {
                name,
                guidelines,
                tags,
            });
            if (data) {
                commit("setName", name);
                commit("setGuidelines", guidelines);
                commit(
                    "setTags",
                    rootState.projects.tags.filter((t) =>
                        data?.tags?.includes(t.pk),
                    ),
                );
                commit("setEditModalOpen", false);
            } else {
                throw new Error("Unable to retrieve project");
            }
        } catch (error) {
            dispatch("alerts/addError", error, { root: true });
        }
        commit("setLoading", false);
    },
    /**
     * Set the ID of the project on the state (happens immediately on page load).
     */
    setId({ commit }, id) {
        commit("setId", id);
    },
    /**
     * Set loading state.
     */
    setLoading({ commit }, loading) {
        commit("setLoading", loading);
    },
    async share({ commit, dispatch, rootState, state }) {
        const { user, group } = rootState.forms.share;
        try {
            const { data } = await shareProject({ projectId: state.id, user, group });
            if (data) {
                // show toast alert on success
                dispatch(
                    "alerts/add",
                    {
                        color: "success",
                        message: `${user ? "User" : "Group"} added successfully`,
                    },
                    { root: true },
                );
                // update share data on frontend
                commit("setSharedWithGroups", data.shared_with_groups);
                commit("setSharedWithUsers", data.shared_with_users);
            } else {
                throw new Error("Unable to add user or group.");
            }
        } catch (error) {
            dispatch("alerts/addError", error, { root: true });
        }
        dispatch("closeShareModal");
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
    setCreateDocumentModalOpen(state, open) {
        state.createDocumentModalOpen = open;
    },
    setDeleteModalOpen(state, open) {
        state.deleteModalOpen = open;
    },
    setDeleteDocumentModalOpen(state, open) {
        state.deleteDocumentModalOpen = open;
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
    setGuidelines(state, guidelines) {
        state.guidelines = guidelines;
    },
    setId(state, id) {
        state.id = id;
    },
    setLoading(state, loading) {
        state.loading = loading;
    },
    setMenuOpen(state, open) {
        state.menuOpen = open;
    },
    setName(state, name) {
        state.name = name;
    },
    setNextPage(state, nextPage) {
        state.nextPage = nextPage;
    },
    setScripts(state, scripts) {
        state.scripts = scripts;
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
    setSlug(state, slug) {
        state.slug = slug;
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
