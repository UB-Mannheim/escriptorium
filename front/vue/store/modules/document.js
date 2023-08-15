import {
    createDocumentMetadata,
    deleteDocument,
    deleteDocumentMetadata,
    editDocument,
    retrieveDocument,
    retrieveDocumentMetadata,
    retrieveDocumentModels,
    retrieveDocumentParts,
    retrieveDocumentTasks,
    retrieveTextualWitnesses,
    retrieveTranscriptionCharacters,
    retrieveTranscriptionCharCount,
    retrieveTranscriptionOntology,
    shareDocument,
    updateDocumentMetadata,
} from "../../../src/api";
import { tagColorToVariant } from "../util/color";
import { getDocumentMetadataCRUD } from "../util/metadata";
import forms from "../util/initialFormState";
import { throttle } from "../util/throttle";

// initial state
const state = () => ({
    deleteModalOpen: false,
    editModalOpen: false,
    id: null,
    lastModified: "",
    linePosition: null,
    loading: {
        document: false,
        models: false,
        parts: false,
        tasks: false,
        transcriptions: false,
        user: false,
    },
    mainScript: "",
    menuOpen: false,
    /**
     * metadata: [{
     *     pk: Number,
     *     key: {
     *         name: String,
     *     },
     *     value: String,
     * }]
     */
    metadata: [],
    /**
     * models: [{
     *     pk: Number,
     *     name: String,
     *     file: String,
     *     file_size: Number,
     *     job: String,
     *     rights: String,
     *     training: Boolean,
     *     accuracy_percent?: Number,
     *     model?: String,
     *     parent?: String,
     * }]
     */
    models: [],
    name: "",
    /**
     * parts: [{
     *     pk: Number,
     *     thumbnail: String,
     *     order: Number,
     *     title: String,
     * }]
     */
    parts: [],
    partsCount: null,
    projectId: null,
    projectName: "",
    readDirection: "",
    /**
     * regionTypes: [{
     *     pk: Number,
     *     name: String,
     * }]
     */
    regionTypes: [],
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
     * tags: [{
     *     name: String,
     *     pk: Number,
     *     variant: Number,
     * }]
     */
    tags: [],
    /**
     * tasks: [{
     *     pk: Number,
     *     document: Number,
     *     workflow_state: Number,
     *     label: String,
     *     messages?: String,
     *     queued_at: String,
     *     started_at: String
     *     done_at: String,
     *     method: String,
     *     user: Number,
     * }]
     */
    tasks: [],
    /**
     * textualWitnesses: [{
     *     name: String,
     *     pk: Number,
     *     owner: String,
     *     file: String,
     * }]
     */
    textualWitnesses: [],
    /**
     * transcriptions: [{
     *     name: String,
     *     pk: Number,
     *     archived: Boolean,
     *     avg_confidence?: Number,
     * }]
     */
    transcriptions: [],
});

const getters = {};

const actions = {
    /**
     * Change the ontology table category and fetch the selected ontology.
     */
    async changeOntologyCategory({ commit, dispatch }, category) {
        commit("ontology/setLoading", true, { root: true });
        commit("ontology/setCategory", category, { root: true });
        try {
            await dispatch("fetchTranscriptionOntology");
        } catch (error) {
            commit("ontology/setLoading", false, { root: true });
            dispatch("alerts/addError", error, { root: true });
        }
        commit("ontology/setLoading", false, { root: true });
    },
    /**
     * Change the selected transcription and fetch its ontology/characters.
     */
    async changeSelectedTranscription(
        { commit, dispatch, state },
        transcriptionId,
    ) {
        commit("transcription/setSelectedTranscription", transcriptionId, {
            root: true,
        });
        // update counts
        const transcription = state.transcriptions.find(
            (t) => t.pk === transcriptionId,
        );
        if (transcription) {
            const { lines_count } = transcription;
            commit("transcription/setLineCount", lines_count, { root: true });
        }
        // kickoff fetch
        try {
            commit("characters/setLoading", true, { root: true });
            commit("ontology/setLoading", true, { root: true });
            commit(
                "transcription/setLoading",
                { key: "characterCount", loading: true },
                { root: true },
            );
            await dispatch("fetchTranscriptionCharacters");
            await dispatch("fetchTranscriptionCharCount");
            await dispatch("fetchTranscriptionOntology");
        } catch (error) {
            dispatch("alerts/addError", error, { root: true });
        }
    },
    /**
     * Close the "delete document" modal.
     */
    closeDeleteModal({ commit }) {
        commit("setDeleteModalOpen", false);
    },
    /**
     * Close the "edit/delete document" menu.
     */
    closeDocumentMenu({ commit }) {
        commit("setMenuOpen", false);
    },
    /**
     * Close the "edit document" modal and clear out state.
     */
    closeEditModal({ commit, state }) {
        commit("setEditModalOpen", false);
        commit(
            "forms/setFormState",
            {
                form: "editDocument",
                formState: {
                    linePosition: state.linePosition,
                    mainScript: state.mainScript,
                    metadata: state.metadata,
                    name: state.name,
                    readDirection: state.readDirection,
                    tags: state.tags.map((tag) => tag.pk),
                    tagName: "",
                },
            },
            { root: true },
        );
    },
    /**
     * Close the "add group or user" modal and clear out state.
     */
    closeShareModal({ commit, dispatch }) {
        commit("setShareModalOpen", false);
        dispatch("forms/clearForm", "share", { root: true });
    },
    /**
     * Handle the user overwriting existing segmentation
     */
    async confirmOverwriteWarning({ dispatch, state }) {
        try {
            await dispatch("tasks/segmentDocument", state.id, { root: true });
            dispatch("tasks/closeModal", "overwriteWarning", { root: true });
            dispatch("tasks/closeModal", "segment", { root: true });
        } catch (error) {
            dispatch("alerts/addError", error, { root: true });
        }
    },
    /**
     * Delete the current document.
     */
    async deleteDocument({ dispatch, commit, state }) {
        commit("setLoading", { key: "document", loading: true });
        try {
            await deleteDocument({ documentId: state.id });
            commit("setDeleteModalOpen", false);
            // TODO: redirect to project on delete
        } catch (error) {
            dispatch("alerts/addError", error, { root: true });
        }
        commit("setLoading", { key: "document", loading: false });
    },
    /**
     * Fetch the current document.
     */
    async fetchDocument({ commit, state, dispatch, rootState }) {
        // set all loading
        Object.keys(state.loading).map((key) =>
            commit("setLoading", { key, loading: true }),
        );
        // fetch document
        const { data } = await retrieveDocument(state.id);
        if (data) {
            commit("setLastModified", data.updated_at);
            commit("setMainScript", data.main_script);
            commit("setReadDirection", data.read_direction);
            commit("setLinePosition", data.line_offset);
            commit("setName", data.name);
            commit("setPartsCount", data.parts_count);
            commit("setProjectId", data.project?.id);
            commit("setProjectName", data.project?.name);
            commit("setRegionTypes", data.valid_block_types);
            // select all region types on forms that have that key
            Object.keys(forms)
                .filter((form) =>
                    Object.prototype.hasOwnProperty.call(
                        forms[form],
                        "regionTypes",
                    ),
                )
                .forEach((form) => {
                    commit(
                        "forms/setFieldValue",
                        {
                            form,
                            field: "regionTypes",
                            value: data.valid_block_types.map((rt) =>
                                rt.pk.toString(),
                            ),
                        },
                        { root: true },
                    );
                });
            commit("setSharedWithGroups", data.shared_with_groups);
            commit("setSharedWithUsers", data.shared_with_users);
            commit(
                "setTags",
                data.tags?.map((tag) => ({
                    ...tag,
                    variant: tagColorToVariant(tag.color),
                })),
            );
            // set form state for the edit modal
            commit(
                "forms/setFormState",
                {
                    form: "editDocument",
                    formState: {
                        linePosition: data.line_offset,
                        mainScript: data.main_script,
                        metadata: state.metadata,
                        name: data.name,
                        readDirection: data.read_direction,
                        tags: state.tags.map((tag) => tag.pk),
                        tagName: "",
                    },
                },
                { root: true },
            );
            // set default text direction for the segment form
            commit(
                "forms/setFieldValue",
                {
                    form: "segment",
                    field: "textDirection",
                    value:
                        data.read_direction === "rtl"
                            ? "horizontal-rl"
                            : "horizontal-lr",
                },
                { root: true },
            );
            if (data.parts_count > 0) {
                // kickoff parts fetch
                try {
                    commit("setLoading", { key: "parts", loading: true });
                    await dispatch("fetchDocumentParts");
                } catch (error) {
                    commit("setLoading", { key: "parts", loading: false });
                    dispatch("alerts/addError", error, { root: true });
                }
            }
            if (data.transcriptions?.length) {
                // set transcription list to non-archived transcriptions
                const transcriptions = data.transcriptions?.filter(
                    (t) => !t.archived,
                );
                commit("setTranscriptions", transcriptions);
                // select the first one in the list if none selected already
                if (!rootState.transcription.selectedTranscription) {
                    commit(
                        "transcription/setSelectedTranscription",
                        transcriptions[0].pk,
                        { root: true },
                    );
                    const { lines_count } = transcriptions[0];
                    commit("transcription/setLineCount", lines_count, {
                        root: true,
                    });
                }
                // kick off the characters and ontology fetching
                try {
                    await dispatch("fetchTranscriptionCharacters");
                    await dispatch("fetchTranscriptionCharCount");
                    await dispatch("fetchTranscriptionOntology");
                } catch (error) {
                    dispatch("alerts/addError", error, { root: true });
                }
            }
            if (data.project?.id) {
                // set project id and fetch all document tags on the project
                try {
                    await commit("project/setId", data.project?.id, {
                        root: true,
                    });
                    await dispatch(
                        { type: "project/fetchProjectDocumentTags" },
                        { root: true },
                    );
                } catch (error) {
                    dispatch("alerts/addError", error, { root: true });
                }
            }
        } else {
            commit("setLoading", { key: "document", loading: false });
            throw new Error("Unable to retrieve document");
        }
        commit("setLoading", { key: "document", loading: false });

        // fetch scripts, metadata, tasks, models, textual witnesses
        await dispatch({ type: "project/fetchScripts" }, { root: true });
        await dispatch("fetchDocumentMetadata");
        await dispatch("fetchDocumentTasks");
        await dispatch("fetchDocumentModels");
        await dispatch({ type: "user/fetchSegmentModels" }, { root: true });
        await dispatch({ type: "user/fetchRecognizeModels" }, { root: true });
        await dispatch("fetchTextualWitnesses");
    },
    /**
     * Fetch the current document's metadata.
     */
    async fetchDocumentMetadata({ commit, state }) {
        const { data } = await retrieveDocumentMetadata(state.id);
        if (data?.results) {
            commit("setMetadata", data.results);
            commit(
                "forms/setFieldValue",
                {
                    form: "editDocument",
                    field: "metadata",
                    value: data.results,
                },
                { root: true },
            );
        } else {
            throw new Error("Unable to retrieve document metadata");
        }
    },
    /**
     * Fetch the current document's models.
     */
    async fetchDocumentModels({ commit, state }) {
        commit("setLoading", { key: "models", loading: true });
        const { data } = await retrieveDocumentModels(state.id);
        if (data?.results) {
            commit("setModels", data.results);
        } else {
            throw new Error("Unable to retrieve document models");
        }
        commit("setLoading", { key: "models", loading: false });
    },
    /**
     * Fetch the current document's most recent images with thumbnails.
     */
    async fetchDocumentParts({ commit, state }) {
        commit("setLoading", { key: "parts", loading: true });
        const { data } = await retrieveDocumentParts({ documentId: state.id });
        if (data?.results) {
            commit(
                "setParts",
                data.results.map((part) => ({
                    ...part,
                    thumbnail: part.image?.thumbnails?.card,
                })),
            );
        } else {
            commit("setLoading", { key: "parts", loading: false });
            throw new Error("Unable to retrieve document images");
        }
        commit("setLoading", { key: "parts", loading: false });
    },
    /**
     * Fetch page 1 of the current document's most recent tasks.
     */
    async fetchDocumentTasks({ commit, state }) {
        commit("setLoading", { key: "tasks", loading: true });
        const { data } = await retrieveDocumentTasks({ documentId: state.id });
        if (data?.results) {
            commit("setTasks", data.results);
        } else {
            commit("setLoading", { key: "tasks", loading: false });
            throw new Error("Unable to retrieve document tasks");
        }
        commit("setLoading", { key: "tasks", loading: false });
    },
    /**
     * Fetch the most recent tasks, but throttle the fetch so it only happens once per 1000ms.
     */
    fetchDocumentTasksThrottled({ commit, dispatch }) {
        commit("setLoading", { key: "tasks", loading: true });
        throttle(function* () {
            yield dispatch("fetchDocumentTasks");
        });
    },
    /**
     * Fetch existing textual witnesses for use in alignment.
     */
    async fetchTextualWitnesses({ commit }) {
        const { data } = await retrieveTextualWitnesses();
        if (data?.results) {
            commit("setTextualWitnesses", data.results);
        } else {
            throw new Error("Unable to retrieve textual witnesses");
        }
    },
    /**
     * Fetch the current transcription's characters, given this document's id from state,
     * plus sorting params from characters Vuex store.
     */
    async fetchTranscriptionCharacters({ commit, state, rootState }) {
        commit("characters/setLoading", true, { root: true });
        const { data } = await retrieveTranscriptionCharacters({
            documentId: state.id,
            transcriptionId: rootState.transcription.selectedTranscription,
            field: rootState.characters.sortState?.field,
            direction: rootState.characters.sortState?.direction,
        });
        if (data?.results) {
            commit("characters/setCharacters", data.results, { root: true });
        } else {
            throw new Error("Unable to retrieve characters");
        }
        commit("characters/setLoading", false, { root: true });
    },
    /**
     * Fetch the number of characters on the currently selected transcription level.
     */
    async fetchTranscriptionCharCount({ commit, state, rootState }) {
        commit(
            "transcription/setLoading",
            { key: "characterCount", loading: true },
            { root: true },
        );
        const { data } = await retrieveTranscriptionCharCount({
            documentId: state.id,
            transcriptionId: rootState.transcription.selectedTranscription,
        });
        if (data?.count) {
            commit("transcription/setCharacterCount", data.count, {
                root: true,
            });
            commit(
                "transcription/setLoading",
                { key: "characterCount", loading: false },
                { root: true },
            );
        } else {
            commit(
                "transcription/setLoading",
                { key: "characterCount", loading: false },
                { root: true },
            );
            throw new Error(
                "Unable to retrieve character count for the selected transcription.",
            );
        }
    },
    /**
     * Fetch the current transcription's ontology, given this document's id from state, plus
     * ontology category and sorting params from ontology Vuex store.
     */
    async fetchTranscriptionOntology({ commit, state, rootState }) {
        commit("ontology/setLoading", true, { root: true });
        const { data } = await retrieveTranscriptionOntology({
            documentId: state.id,
            transcriptionId: rootState.transcription.selectedTranscription,
            category: rootState.ontology.category,
            sortField: rootState.ontology.sortState?.field,
            sortDirection: rootState.ontology.sortState?.direction,
        });
        if (data?.results) {
            commit("ontology/setOntology", data.results, { root: true });
            commit("ontology/setLoading", false, { root: true });
        } else {
            commit("ontology/setLoading", false, { root: true });
            throw new Error(
                `Unable to retrieve ${rootState.ontology.category} ontology`,
            );
        }
    },
    /**
     * Handle submitting the alignment modal. Queue the task and close the modal.
     */
    async handleSubmitAlign({ dispatch, state }) {
        try {
            await dispatch("tasks/alignDocument", state.id, { root: true });
            dispatch("tasks/closeModal", "align", { root: true });
            dispatch({ type: "sidebar/closeSidebar" }, { root: true });
            // show toast alert on success
            dispatch(
                "alerts/add",
                {
                    color: "success",
                    message: "Alignment queued successfully",
                },
                { root: true },
            );
        } catch (error) {
            dispatch("alerts/addError", error, { root: true });
        }
    },
    /**
     * Handle submitting the export modal. Queue the task and close the modal.
     */
    async handleSubmitExport({ dispatch, state }) {
        try {
            await dispatch("tasks/exportDocument", state.id, { root: true });
            dispatch("tasks/closeModal", "export", { root: true });
            dispatch({ type: "sidebar/closeSidebar" }, { root: true });
            // show toast alert on success
            dispatch(
                "alerts/add",
                {
                    color: "success",
                    message: "Export queued successfully",
                },
                { root: true },
            );
        } catch (error) {
            dispatch("alerts/addError", error, { root: true });
        }
    },
    /**
     * Handle submitting the import modal. Queue the task and close the modal.
     */
    async handleSubmitImport({ commit, dispatch, rootState, state }) {
        try {
            await dispatch("tasks/importImagesOrTranscription", state.id, {
                root: true,
            });
            const isImages = rootState?.forms?.import?.mode === "images";
            dispatch("tasks/closeModal", "import", { root: true });
            dispatch({ type: "sidebar/closeSidebar" }, { root: true });
            // show toast alert on success
            dispatch(
                "alerts/add",
                {
                    color: "success",
                    message: "Import queued successfully",
                },
                { root: true },
            );
            // if importing images, refresh images
            if (isImages) {
                try {
                    commit("setLoading", { key: "parts", loading: true });
                    await dispatch("fetchDocumentParts");
                    commit("setLoading", { key: "parts", loading: false });
                } catch (error) {
                    commit("setLoading", { key: "parts", loading: false });
                    dispatch("alerts/addError", error, { root: true });
                }
            }
        } catch (error) {
            dispatch("alerts/addError", error, { root: true });
        }
    },
    /**
     * Handle submitting the segmentation modal. Open the confirm overwrite modal if overwrite
     * is checked, otherwise just queue the segmentation task and close the modal.
     */
    async handleSubmitSegmentation({ commit, dispatch, state, rootState }) {
        if (rootState?.forms?.segment?.overwrite === true) {
            dispatch("tasks/openModal", "overwriteWarning", { root: true });
        } else {
            commit("setLoading", { key: "document", loading: true });
            try {
                await dispatch("tasks/segmentDocument", state.id, {
                    root: true,
                });
                dispatch("tasks/closeModal", "segment", { root: true });
                // set default text direction for the segment form
                commit(
                    "forms/setFieldValue",
                    {
                        form: "segment",
                        field: "textDirection",
                        value:
                            state.readDirection === "rtl"
                                ? "horizontal-rl"
                                : "horizontal-lr",
                    },
                    { root: true },
                );
                dispatch({ type: "sidebar/closeSidebar" }, { root: true });
                // show toast alert on success
                dispatch(
                    "alerts/add",
                    {
                        color: "success",
                        message: "Segmentation queued successfully",
                    },
                    { root: true },
                );
            } catch (error) {
                commit("setLoading", { key: "document", loading: false });
                dispatch("alerts/addError", error, { root: true });
            }
            commit("setLoading", { key: "document", loading: false });
        }
    },
    /**
     * Handle submitting the transcribe modal: just queue the task and close the modal.
     */
    async handleSubmitTranscribe({ commit, dispatch, state }) {
        commit("setLoading", { key: "document", loading: true });
        try {
            await dispatch("tasks/transcribeDocument", state.id, {
                root: true,
            });
            dispatch("tasks/closeModal", "transcribe", { root: true });
            dispatch({ type: "sidebar/closeSidebar" }, { root: true });
            // show toast alert on success
            dispatch(
                "alerts/add",
                {
                    color: "success",
                    message: "Transcription queued successfully",
                },
                { root: true },
            );
        } catch (error) {
            commit("setLoading", { key: "document", loading: false });
            dispatch("alerts/addError", error, { root: true });
        }
        commit("setLoading", { key: "document", loading: false });
    },
    /**
     * Open the "delete document" modal.
     */
    openDeleteModal({ commit }) {
        commit("setDeleteModalOpen", true);
    },
    /**
     * Open the "edit/delete document" menu.
     */
    openDocumentMenu({ commit }) {
        commit("setMenuOpen", true);
    },
    /**
     * Open the "edit document" modal.
     */
    openEditModal({ commit }) {
        commit("setEditModalOpen", true);
    },
    /**
     * Open the "groups and users" modal.
     */
    openShareModal({ commit }) {
        commit("setShareModalOpen", true);
    },
    /**
     * Save changes to the document made in the edit modal.
     */
    async saveDocument({ commit, dispatch, rootState, state }) {
        commit("setLoading", { key: "document", loading: true });
        // get form state
        const {
            linePosition,
            mainScript,
            metadata,
            name,
            readDirection,
            tags,
        } = rootState.forms.editDocument;
        // split modified metadata by operation
        const {
            metadataToCreate,
            metadataToUpdate,
            metadataToDelete,
        } = getDocumentMetadataCRUD({
            stateMetadata: state.metadata,
            formMetadata: metadata,
        });
        try {
            const [documentResponse, ...metadataResponses] = await Promise.all([
                // update the document
                editDocument(state.id, {
                    linePosition,
                    mainScript,
                    name,
                    readDirection,
                    tags,
                }),
                // create, update, delete metadata as needed
                ...metadataToCreate.map((metadatum) =>
                    createDocumentMetadata({
                        documentId: state.id,
                        metadatum,
                    }),
                ),
                ...metadataToUpdate.map((metadatum) =>
                    updateDocumentMetadata({
                        documentId: state.id,
                        metadatum,
                    }),
                ),
                ...metadataToDelete.map((m) =>
                    deleteDocumentMetadata({
                        documentId: state.id,
                        metadatumId: m.pk,
                    }),
                ),
            ]);
            // update state for metadata responses
            metadataResponses
                .filter((r) => !!r)
                .forEach((response) => {
                    if (response.status === 200) {
                        // updated
                        const { data } = response;
                        commit("addMetadatum", data);
                    } else if (response.status === 201) {
                        // created
                        const { data } = response;
                        commit("updateMetadatum", data);
                    } else if (response.status === 204) {
                        // deleted
                        const { request } = response;
                        const pk = request?.responseURL.split("/").slice(-1);
                        commit("removeMetadatum", pk);
                    } else {
                        throw new Error("Error updating metadata");
                    }
                });
            // update state for document response
            if (documentResponse?.data) {
                commit("setName", name);
                commit("setLinePosition", linePosition);
                commit("setMainScript", mainScript);
                commit("setReadDirection", readDirection);
                commit(
                    "setTags",
                    rootState.project.documentTags.filter((t) =>
                        documentResponse.data.tags?.includes(t.pk),
                    ),
                );
                commit("setEditModalOpen", false);
            } else {
                throw new Error("Unable to save document");
            }
            // show toast alert on success
            dispatch(
                "alerts/add",
                {
                    color: "success",
                    message: "Document updated successfully",
                },
                { root: true },
            );
        } catch (error) {
            commit("setLoading", { key: "document", loading: false });
            dispatch("alerts/addError", error, { root: true });
        }
        commit("setLoading", { key: "document", loading: false });
    },
    /**
     * Set the ID of the document on the state (happens immediately on page load).
     */
    setId({ commit }, id) {
        commit("setId", id);
    },
    /**
     * Set the loading state.
     */
    setLoading({ commit }, { key, loading }) {
        commit("setLoading", { key, loading });
    },
    /**
     * Send a POST request to share the document with users and groups from the share form.
     */
    async shareDocument({ commit, dispatch, state, rootState }) {
        commit("setLoading", { key: "document", loading: true });
        const { user, group } = rootState.forms.share;
        try {
            const { data } = await shareDocument({
                documentId: state.id,
                user,
                group,
            });
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
            commit("setLoading", { key: "document", loading: false });
            dispatch("alerts/addError", error, { root: true });
        }
        commit("setLoading", { key: "document", loading: false });
        dispatch("closeShareModal");
    },
    /**
     * Change the characters sort field and perform another fetch for characters.
     */
    async sortCharacters({ commit, dispatch }, field) {
        let direction = 1;
        if (field === "frequency") {
            direction = -1;
        }
        commit("characters/setSortState", { field, direction }, { root: true });
        try {
            await dispatch("fetchTranscriptionCharacters");
        } catch (error) {
            commit("characters/setLoading", false, { root: true });
            dispatch("alerts/addError", error, { root: true });
        }
    },
    /**
     * Event handler for sorting the ontology table; sets the sort state on the
     * ontology Vuex store, then makes a call to fetch ontology based on current state.
     */
    async sortOntology({ commit, dispatch }, { field, direction }) {
        commit("ontology/setSortState", { field, direction }, { root: true });
        try {
            await dispatch("fetchTranscriptionOntology");
        } catch (error) {
            commit("ontology/setLoading", false, { root: true });
            dispatch("alerts/addError", error, { root: true });
        }
    },
};

const mutations = {
    addMetadatum(state, metadatum) {
        const metadata = structuredClone(state.metadata);
        metadata.push(metadatum);
        state.metadata = metadata;
    },
    removeMetadatum(state, removePk) {
        const clone = structuredClone(state.metadata);
        state.metadata = clone.filter(
            (metadatum) => metadatum.pk.toString() !== removePk.toString(),
        );
    },
    setDeleteModalOpen(state, open) {
        state.deleteModalOpen = open;
    },
    setEditModalOpen(state, open) {
        state.editModalOpen = open;
    },
    setId(state, id) {
        state.id = id;
    },
    setLastModified(state, lastModified) {
        state.lastModified = lastModified;
    },
    setLinePosition(state, linePosition) {
        state.linePosition = linePosition;
    },
    setLoading(state, { key, loading }) {
        const clone = structuredClone(state.loading);
        clone[key] = loading;
        state.loading = clone;
    },
    setMainScript(state, mainScript) {
        state.mainScript = mainScript;
    },
    setMenuOpen(state, open) {
        state.menuOpen = open;
    },
    setMetadata(state, metadata) {
        state.metadata = metadata;
    },
    setModels(state, models) {
        state.models = models;
    },
    setName(state, name) {
        state.name = name;
    },
    setParts(state, parts) {
        state.parts = parts;
    },
    setPartsCount(state, partsCount) {
        state.partsCount = partsCount;
    },
    setProjectId(state, projectId) {
        state.projectId = projectId;
    },
    setProjectName(state, projectName) {
        state.projectName = projectName;
    },
    setReadDirection(state, readDirection) {
        state.readDirection = readDirection;
    },
    setRegionTypes(state, regionTypes) {
        state.regionTypes = regionTypes;
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
    setTasks(state, tasks) {
        state.tasks = tasks;
    },
    setTags(state, tags) {
        state.tags = tags;
    },
    setTextualWitnesses(state, textualWitnesses) {
        state.textualWitnesses = textualWitnesses;
    },
    setTranscriptions(state, transcriptions) {
        state.transcriptions = transcriptions;
    },
    updateMetadatum(state, metadatumToUpdate) {
        const metadata = structuredClone(state.metadata).map((m) => {
            if (m.pk.toString() === metadatumToUpdate.pk.toString()) {
                return metadatumToUpdate;
            }
            return m;
        });
        state.metadata = metadata;
    },
};

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations,
};
