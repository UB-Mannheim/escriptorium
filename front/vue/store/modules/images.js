import axios from "axios";
import {
    bulkMoveParts,
    deleteDocumentPart,
    moveDocumentPart,
    retrieveDocument,
    retrieveDocumentParts,
} from "../../../src/api";
import forms from "../util/initialFormState";

// initial state
const state = () => ({
    deleteModalOpen: false,
    isDragging: false,
    loading: {
        document: true,
        groups: true,
        images: true,
        models: true,
    },
    moveModalOpen: false,
    nextPage: "",
    partTitleToDelete: "",
    selectedParts: [],
});

const getters = {};

const actions = {
    /**
     * Close the delete confirmation modal.
     */
    closeDeleteModal({ commit }, part) {
        if (part) {
            // if this was just for a single part from context menu, remove the selection
            commit("setSelectedParts", []);
            commit("setPartTitleToDelete", "");
        }
        commit("setDeleteModalOpen", false);
    },
    /**
     * Handle the user overwriting existing segmentation
     */
    async confirmOverwriteWarning({ commit, dispatch }) {
        try {
            commit("setLoading", { key: "images", loading: true });
            await dispatch("document/confirmOverwriteWarning", null, {
                root: true,
            });
            commit("setSelectedParts", []);
            commit("setLoading", { key: "images", loading: false });
        } catch (error) {
            commit("setLoading", { key: "images", loading: false });
            dispatch("alerts/addError", error, { root: true });
        }
    },
    /**
     * Delete the selected parts, close the modal, and update the count.
     */
    async deleteSelectedParts({ commit, dispatch, rootState, state }) {
        commit("setLoading", { key: "images", loading: true });
        try {
            // delete each selected part
            await Promise.all(
                state.selectedParts.map(async (pk) => {
                    return await deleteDocumentPart({
                        documentId: rootState.document.id,
                        partPk: pk,
                    });
                }),
            );

            // re-fetch parts and update count
            await dispatch("fetchParts");
            commit(
                "document/setPartsCount",
                rootState.document.partsCount - state.selectedParts.length,
                { root: true },
            );

            // deselect deleted parts
            commit("setSelectedParts", []);

            // give user success feedback and close modal
            dispatch(
                "alerts/add",
                {
                    color: "success",
                    message: "Image(s) deleted successfully",
                },
                { root: true },
            );
            commit("setDeleteModalOpen", false);
        } catch (error) {
            dispatch("alerts/addError", error, { root: true });
        }
        commit("setLoading", { key: "images", loading: false });
    },
    /**
     * Fetch the document and its images, and set on state.
     */
    async fetchDocument({ commit, dispatch, rootState }) {
        commit("setLoading", { key: "document", loading: true });
        const { data } = await retrieveDocument(rootState.document.id);
        if (data) {
            commit("document/setReadDirection", data.read_direction, {
                root: true,
            });
            commit("document/setName", data.name, { root: true });
            commit("document/setPartsCount", data.parts_count, { root: true });
            commit("document/setProjectSlug", data.project, { root: true });
            commit("document/setProjectId", data.project_id, { root: true });
            commit("document/setProjectName", data.project_name, {
                root: true,
            });
            await commit(
                "document/setRegionTypes",
                [
                    ...data.valid_block_types,
                    { pk: "Undefined", name: "(Undefined region type)" },
                    { pk: "Orphan", name: "(Orphan lines)" },
                ],
                { root: true },
            );
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
                            value: rootState.document.regionTypes.map((rt) =>
                                rt.pk.toString(),
                            ),
                        },
                        { root: true },
                    );
                });

            // set groups/users
            commit("document/setSharedWithGroups", data.shared_with_groups, {
                root: true,
            });
            commit("document/setSharedWithUsers", data.shared_with_users, {
                root: true,
            });

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
            if (data.transcriptions?.length) {
                // set transcription list to non-archived transcriptions
                const transcriptions = data.transcriptions?.filter(
                    (t) => !t.archived,
                );
                commit("document/setTranscriptions", transcriptions, {
                    root: true,
                });
            }

            commit("setLoading", { key: "document", loading: false });

            if (data.parts_count > 0) {
                // kickoff parts fetch
                commit("setLoading", { key: "images", loading: true });
                try {
                    await dispatch("fetchParts");
                    commit("setLoading", { key: "images", loading: false });
                } catch (error) {
                    commit("setLoading", { key: "images", loading: false });
                    dispatch("alerts/addError", error, { root: true });
                }
            } else {
                commit("setLoading", { key: "images", loading: false });
            }
        } else {
            commit("setLoading", { key: "document", loading: false });
            throw new Error("Unable to retrieve document");
        }
        // fetch textual witnesses
        await dispatch("document/fetchTextualWitnesses", null, { root: true });
    },
    /**
     * Fetch the next page of images, retrieved from fetchImages, and add
     * all of its projects on the state.
     */
    async fetchNextPage({ state, commit, rootState }) {
        const { data } = await axios.get(state.nextPage);
        if (data?.results) {
            data.results.forEach((part) => {
                commit(
                    "document/addPart",
                    {
                        ...part,
                        title: `${part.title} - ${part.filename}`,
                        thumbnail: part.image?.thumbnails?.card,
                        href: `/document/${rootState.document.id}/part/${part.pk}/edit/`,
                    },
                    { root: true },
                );
            });
            commit("setNextPage", data.next || "");
        } else {
            throw new Error("Unable to retrieve additional images");
        }
    },
    /**
     * Fetch the images with thumbnails.
     */
    async fetchParts({ commit, rootState }) {
        const { data } = await retrieveDocumentParts({
            documentId: rootState.document.id,
            field: "order",
            direction: 1,
            pageSize: 50,
        });
        if (data?.results) {
            commit(
                "document/setParts",
                data.results.map((part) => ({
                    ...part,
                    title: `${part.title} - ${part.filename}`,
                    thumbnail: part.image?.thumbnails?.card,
                    href: `/document/${rootState.document.id}/part/${part.pk}/edit/`,
                })),
                { root: true },
            );
            commit("setNextPage", data.next || "");
        } else {
            throw new Error("Unable to retrieve document images");
        }
    },
    /**
     * Fetch all images currently loaded, and update if any have changed.
     * Use the optional "fields" param to specify fields; otherwise only checks order.
     */
    async fetchUpdatedParts({ commit, rootState }, fields = ["order"]) {
        // figure out how many parts are loaded now
        const partsToLoadCount = rootState.document.parts.length;
        const loops = Math.ceil(partsToLoadCount / 50);
        const allResultParts = [];
        let nextPage = null;
        // loop only as many times as necessary to reach that number
        for (let i = 0; i < loops; i++) {
            let data = null;
            if (i === 0) {
                // first loop: fetch first page
                const res = await retrieveDocumentParts({
                    documentId: rootState.document.id,
                    field: "order",
                    direction: 1,
                    pageSize: 50,
                });
                data = res.data;
            } else if (nextPage) {
                // fetch next page on subsequent loops
                const res = await axios.get(nextPage);
                data = res.data;
            }
            if (data?.results) {
                const resultParts = data.results.map((part) => ({
                    ...part,
                    title: `${part.title} - ${part.filename}`,
                    thumbnail: part.image?.thumbnails?.card,
                    href: `/document/${rootState.document.id}/part/${part.pk}/edit/`,
                }));
                // find new or changed parts for add/update operation
                resultParts.forEach((part) => {
                    const foundPart = rootState.document.parts.find(
                        (p) => p.pk.toString() === part.pk.toString(),
                    );
                    // check for changes on specified field(s)
                    if (
                        foundPart &&
                        fields.some((field) => foundPart[field] !== part[field])
                    ) {
                        commit("document/updatePart", part, { root: true });
                    } else if (!foundPart) {
                        // if the part isn't present at all, add it. this could happen
                        // if a part is moved to the bottom of the list and not all
                        // parts have been loaded
                        commit("document/addPart", part, { root: true });
                    }
                });
                // store all parts for final comparison
                allResultParts.push(...resultParts);
                // set next page
                nextPage = data.next || "";
            }
        }
        // remove from state any parts that should no longer be visible
        const toRemove = rootState.document.parts.filter(
            (p) =>
                !allResultParts.some(
                    (part) => p.pk.toString() === part.pk.toString(),
                ),
        );
        toRemove.forEach((part) =>
            commit("document/removePart", part.pk, { root: true }),
        );
    },
    /**
     * Handle submitting the align modal.
     */
    async handleSubmitAlign({ commit, dispatch }) {
        try {
            commit("setLoading", { key: "images", loading: true });
            await dispatch("document/handleSubmitAlign", null, {
                root: true,
            });
            commit("setSelectedParts", []);
            commit("setLoading", { key: "images", loading: false });
        } catch (error) {
            commit("setLoading", { key: "images", loading: false });
            dispatch("alerts/addError", error, { root: true });
        }
    },
    /**
     * Handle submitting the export modal.
     */
    async handleSubmitExport({ commit, dispatch }) {
        try {
            commit("setLoading", { key: "images", loading: true });
            await dispatch("document/handleSubmitExport", null, {
                root: true,
            });
            commit("setSelectedParts", []);
            commit("setLoading", { key: "images", loading: false });
        } catch (error) {
            commit("setLoading", { key: "images", loading: false });
            dispatch("alerts/addError", error, { root: true });
        }
    },
    /**
     * Handle submitting the segmentation modal.
     */
    async handleSubmitSegmentation({ commit, dispatch, rootState }) {
        try {
            await dispatch("document/handleSubmitSegmentation", null, {
                root: true,
            });
            if (rootState?.forms?.segment?.overwrite !== true) {
                commit("setSelectedParts", []);
                commit("setLoading", { key: "images", loading: false });
            }
        } catch (error) {
            commit("setLoading", { key: "images", loading: false });
            dispatch("alerts/addError", error, { root: true });
        }
    },
    /**
     * Handle submitting the model training modal.
     */
    async handleSubmitTraining({ commit, dispatch, rootState, state }) {
        try {
            commit("setLoading", { key: "images", loading: true });
            await dispatch(
                "tasks/trainModel",
                {
                    documentId: rootState.document.id,
                    parts: state.selectedParts,
                    modelType: rootState.tasks.modalOpen.trainSegmenter
                        ? "segmenter"
                        : "recognizer",
                },
                { root: true },
            );
            dispatch("tasks/closeModal", "trainSegmenter", { root: true });
            dispatch("tasks/closeModal", "trainRecognizer", { root: true });
            commit("setSelectedParts", []);
            commit("setLoading", { key: "images", loading: false });
            // show toast alert on success
            dispatch(
                "alerts/add",
                {
                    color: "success",
                    message: "Training queued successfully",
                },
                { root: true },
            );
        } catch (error) {
            commit("setLoading", { key: "images", loading: false });
            dispatch("alerts/addError", error, { root: true });
        }
    },
    /**
     * Handle submitting the transcribe modal.
     */
    async handleSubmitTranscribe({ commit, dispatch }) {
        try {
            commit("setLoading", { key: "images", loading: true });
            await dispatch("document/handleSubmitTranscribe", null, {
                root: true,
            });
            commit("setSelectedParts", []);
            commit("setLoading", { key: "images", loading: false });
        } catch (error) {
            commit("setLoading", { key: "images", loading: false });
            dispatch("alerts/addError", error, { root: true });
        }
    },
    /**
     * Move the selected images to the specified index.
     * (if index is -1, move to the end of the list of parts.)
     */
    async moveSelectedParts({ commit, dispatch, rootState, state }, { index }) {
        commit("setLoading", { key: "images", loading: true });
        try {
            await bulkMoveParts({
                documentId: rootState.document.id,
                parts: state.selectedParts,
                index,
            });
            await dispatch("fetchUpdatedParts");
            commit("setSelectedParts", []);
            commit("setLoading", { key: "images", loading: false });
        } catch (error) {
            commit("setLoading", { key: "images", loading: false });
            dispatch("alerts/addError", error, { root: true });
        }
    },
    /**
     * Move a single image to the specified index.
     */
    async movePart({ commit, dispatch, rootState }, { partPk, index }) {
        commit("setLoading", { key: "images", loading: true });
        try {
            await moveDocumentPart({
                documentId: rootState.document.id,
                partId: partPk,
                index,
            });
            await dispatch("fetchUpdatedParts");
            commit("setSelectedParts", []);
            commit("setLoading", { key: "images", loading: false });
        } catch (error) {
            commit("setLoading", { key: "images", loading: false });
            dispatch("alerts/addError", error, { root: true });
        }
    },
    /**
     * Open the delete confirmation modal for a part.
     */
    openDeleteModal({ commit }, part) {
        if (part) {
            // if this was just for a single part from context menu, set the selection
            commit("setSelectedParts", [part.pk]);
            commit("setPartTitleToDelete", part.title);
        }
        commit("setDeleteModalOpen", true);
    },
    /**
     * Open the move modal
     */
    openMoveModal({ commit }) {
        commit("setMoveModalOpen", true);
    },
    /**
     * Submit the move modal
     */
    async onSubmitMove({ commit, dispatch, rootState }) {
        // get form state: index and whether it's before/after that index
        const { index, location } = rootState.forms.moveImages;
        const idx = location === "before" ? index - 1 : index;
        // move
        await dispatch("moveSelectedParts", { index: idx });
        commit("setMoveModalOpen", false);
        dispatch("forms/clearForm", "moveImages", { root: true });
    },
    /**
     * Close the move modal and reset its form state
     */
    onCancelMove({ commit, dispatch }) {
        commit("setMoveModalOpen", false);
        dispatch("forms/clearForm", "moveImages", { root: true });
    },
    /**
     * Set selected parts by passing an array of numbers, which correspond to the `order` attribute
     * of the desired parts.
     */
    setSelectedPartsByOrder({ commit, rootState }, selected) {
        const parts = rootState.document.parts
            .filter((part) => selected.includes(part.order + 1))
            .map((part) => part.pk);
        commit("setSelectedParts", parts);
    },
    /**
     * Modify the selected parts list by adding or removing, using an array of numbers which
     * correspond to the `order` attribute to determine which parts to add/remove. Use the
     * `checked` parameter to tell whether to add (true) or remove (false).
     */
    modifySelectedPartsByOrder({ commit, rootState, state }, { selected, checked }) {
        const partPksByOrder = rootState.document.parts
            .filter((part) => selected.includes(part.order + 1))
            .map((part) => part.pk);
        let selectedPartsClone = structuredClone(state.selectedParts);
        if (checked) {
            partPksByOrder.forEach((partPk) => {
                if (!selectedPartsClone.includes(partPk)) {
                    selectedPartsClone.push(partPk);
                }
            });
        } else {
            selectedPartsClone = selectedPartsClone.filter(
                (partPk) => !partPksByOrder.includes(partPk)
            );
        }
        commit("setSelectedParts", selectedPartsClone);
    },
    /**
     * Select or deselect a part, depending on its current state.
     */
    togglePartSelected({ commit, state }, pk) {
        if (state.selectedParts.includes(pk)) {
            commit("deselectPart", pk);
        } else {
            commit("selectPart", pk);
        }
    },
};

const mutations = {
    deselectPart(state, partPk) {
        const clone = structuredClone(state.selectedParts);
        clone.splice(clone.indexOf(partPk), 1);
        state.selectedParts = clone;
    },
    selectPart(state, partPk) {
        const clone = structuredClone(state.selectedParts);
        clone.push(partPk);
        state.selectedParts = clone;
    },
    setDeleteModalOpen(state, open) {
        state.deleteModalOpen = open;
    },
    setIsDragging(state, isDragging) {
        state.isDragging = isDragging;
    },
    setLoading(state, { key, loading }) {
        state.loading[key] = loading;
    },
    setMoveModalOpen(state, open) {
        state.moveModalOpen = open;
    },
    setNextPage(state, nextPage) {
        state.nextPage = nextPage;
    },
    setPartTitleToDelete(state, partTitle) {
        state.partTitleToDelete = partTitle;
    },
    setSelectedParts(state, parts) {
        state.selectedParts = parts;
    },
};

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations,
};
