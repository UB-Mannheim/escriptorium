import { SCRIPT_NAME } from '../../../src/scriptname.js';
import axios from "axios";
import {
    clearProjectOntology,
    createDocument,
    createDocumentMetadata,
    createProjectDocumentTag,
    deleteDocument,
    deleteProject,
    editProject,
    exportProjectOntology,
    importProjectOntology,
    retrieveDocumentsList,
    retrieveFonts,
    retrieveProject,
    retrieveProjectDocumentTags,
    retrieveProjectOntology,
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
    documentToDelete: null,
    deleteModalOpen: false,
    deleteDocumentModalOpen: false,
    editModalOpen: false,
    guidelines: "",
    id: null,
    loading: true,
    menuOpen: false,
    name: "",
    nextPage: "",
    transcriptionFont: null,
    /** fonts: [{ pk, name, url, size_adjust }] */
    fonts: [],
    /**
     * The project's default ontology config (applied to every new document
     * of this project), or null if unset.
     */
    ontologyConfig: null,
    /**
     * scripts: [{
     *     id: Number,
     *     name: String,
     *     text_direction: String,
     * }]
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
                    transcriptionFont: state.transcriptionFont || "",
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
     * Close the "delete document" modal.
     */
    closeDeleteDocumentModal({ commit }) {
        commit("setDeleteDocumentModalOpen", false);
    },
    /**
     * Close the "edit/delete project" menu.
     */
    closeProjectMenu({ commit }) {
        commit("setMenuOpen", false);
    },
    /**
     * Close the "add group or user" modal and clear out state.
     */
    closeShareModal({ commit, dispatch }) {
        commit("setShareModalOpen", false);
        dispatch("forms/clearForm", "share", { root: true });
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
                transcriptionFont: rootState.forms?.editDocument?.transcriptionFont,
            });
            if (data) {
                // try to create metadata too
                await Promise.all(
                    rootState.forms?.editDocument?.metadata.map((metadatum) =>
                        createDocumentMetadata({
                            documentId: data.pk,
                            metadatum,
                        }),
                    ),
                );
                // show toast alert on success
                dispatch(
                    "alerts/add",
                    {
                        color: "success",
                        message: "Document created successfully",
                    },
                    { root: true },
                );
                // redirect to new document
                window.location = SCRIPT_NAME + `/document/${data.pk}/`;
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
                    "forms/addToArray",
                    { form: "editDocument", field: "tags", value: data.pk },
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
    async deleteDocument({ dispatch, commit, state }) {
        commit("setLoading", true);
        try {
            await deleteDocument({ documentId: state?.documentToDelete?.pk });
            await dispatch("fetchProjectDocuments");
            commit("setDeleteDocumentModalOpen", false);
            // show toast alert on success
            dispatch(
                "alerts/add",
                {
                    color: "success",
                    message: "Document deleted successfully",
                },
                { root: true },
            );
        } catch (error) {
            dispatch("alerts/addError", error, { root: true });
        }
        commit("setLoading", false);
    },
    async deleteProject({ dispatch, commit, state }) {
        commit("setLoading", true);
        try {
            await deleteProject(state.id);
            dispatch(
                "alerts/add",
                {
                    color: "success",
                    message: "Project deleted successfully",
                },
                { root: true },
            );
            commit("setDeleteModalOpen", false);
            window.location = SCRIPT_NAME + "/projects/";
        } catch (error) {
            dispatch("alerts/addError", error, { root: true });
        }
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
                    commit("addDocument", {
                        ...document,
                        tags: { tags: document.tags },
                        // link to document dashboard
                        href: SCRIPT_NAME + `/document/${document.pk}/`,
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
            commit("setGuidelines", data.guidelines);
            commit("setTranscriptionFont", data.transcription_font || null);
            const tagPks = data.tags.map((tag) => tag.pk);
            commit(
                "setTags",
                rootState.projects.tags.filter((t) => tagPks.includes(t.pk)),
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
                        tags: tagPks,
                        tagColor: "",
                        tagName: "",
                        transcriptionFont: data.transcription_font || "",
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
        await dispatch("fetchFonts");
        await dispatch("fetchProjectOntology");
    },
    /**
     * Fetch the project's default ontology config, if any.
     */
    async fetchProjectOntology({ commit, state, dispatch }) {
        try {
            const { data } = await retrieveProjectOntology(state.id);
            commit("setOntologyConfig", data || null);
        } catch (error) {
            dispatch("alerts/addError", error, { root: true });
        }
    },
    /**
     * Import an ontology config file (YAML or legacy JSON) as this
     * project's default ontology, applied to every new document.
     */
    async importOntology({ commit, state, dispatch }, file) {
        try {
            const { data } = await importProjectOntology(state.id, file);
            commit("setOntologyConfig", data || null);
            dispatch(
                "alerts/add",
                { color: "success", message: "Default ontology imported successfully" },
                { root: true },
            );
        } catch (error) {
            dispatch("alerts/addError", error, { root: true });
        }
    },
    /**
     * Download the project's default ontology config as a YAML file.
     */
    async exportOntology({ state, dispatch }) {
        try {
            const { data } = await exportProjectOntology(state.id);
            const url = window.URL.createObjectURL(new Blob([data]));
            const link = document.createElement("a");
            link.href = url;
            link.setAttribute("download", "ontology_export.yml");
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);
        } catch (error) {
            dispatch("alerts/addError", error, { root: true });
        }
    },
    /**
     * Clear the project's default ontology config.
     */
    async clearOntology({ commit, state, dispatch }) {
        try {
            await clearProjectOntology(state.id);
            commit("setOntologyConfig", null);
            dispatch(
                "alerts/add",
                { color: "success", message: "Default ontology cleared" },
                { root: true },
            );
        } catch (error) {
            dispatch("alerts/addError", error, { root: true });
        }
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
        } else {
            commit("setNextPage", "");
        }
        if (data?.results) {
            commit(
                "setDocuments",
                data.results.map((result) => ({
                    ...result,
                    tags: { tags: result.tags },
                    // link to document dashboard
                    href: SCRIPT_NAME + `/document/${result.pk}/`,
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
            commit("setScripts", data.results);
        } else {
            throw new Error("Unable to retrieve scripts");
        }
    },
    async fetchFonts({ commit }) {
        const { data } = await retrieveFonts();
        if (data?.results) {
            commit("setFonts", data.results);
        } else {
            throw new Error("Unable to retrieve fonts");
        }
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
    openDeleteDocumentModal({ commit }, item) {
        // set which document to delete, then open the modal
        commit("setDocumentToDelete", item);
        commit("setDeleteDocumentModalOpen", true);
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
        const { name, guidelines, tags, transcriptionFont } = rootState.forms.editProject;
        try {
            const { data } = await editProject(state.id, {
                name,
                guidelines,
                tags,
                transcriptionFont,
            });
            if (data) {
                commit("setName", name);
                commit("setGuidelines", guidelines);
                commit("setTranscriptionFont", transcriptionFont || null);
                const tagPks = data.tags.map((tag) => tag.pk);
                commit(
                    "setTags",
                    rootState.projects.tags.filter((t) =>
                        tagPks.includes(t.pk),
                    ),
                );
                commit("setEditModalOpen", false);
            } else {
                throw new Error("Unable to retrieve project");
            }
        } catch (error) {
            commit("setLoading", false);
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
    /**
     * Share a project with a group or user, then update based on returned data.
     */
    async share({ commit, dispatch, rootState, state }) {
        const { user, group } = rootState.forms.share;
        const params = { projectId: state.id };
        if (user) params["user"] = user;
        else if (group) params["group"] = group;
        try {
            const { data } = await shareProject(params);
            if (data) {
                // show toast alert on success
                dispatch(
                    "alerts/add",
                    {
                        color: "success",
                        message: `${
                            user ? "User" : "Group"
                        } added successfully`,
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
        commit("setLoading", true);
        try {
            await dispatch("fetchProjectDocuments");
        } catch (error) {
            dispatch("alerts/addError", error, { root: true });
        }
        commit("setLoading", false);
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
    setDocumentToDelete(state, pk) {
        state.documentToDelete = pk;
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
    setOntologyConfig(state, ontologyConfig) {
        state.ontologyConfig = ontologyConfig;
    },
    setScripts(state, scripts) {
        state.scripts = scripts;
    },
    setFonts(state, fonts) {
        state.fonts = fonts;
    },
    setTranscriptionFont(state, font) {
        state.transcriptionFont = font || null;
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
