import {
    alignDocument,
    cancelTask,
    createTranscriptionLayer,
    exportDocument,
    queueImport,
    segmentDocument,
    transcribeDocument,
} from "../../../src/api";
import initialFormState from "../util/initialFormState";

// initial state
const state = () => ({
    modalOpen: {
        align: false,
        cancelWarning: false,
        export: false,
        import: false,
        overwriteWarning: false,
        segment: false,
        transcribe: false,
    },
    selectedTask: undefined,
});

const getters = {};

const actions = {
    /**
     * Queue the alignment task for a document, passing in the correct type of witness
     * (selected existing or upload), and the correct choice of beam size or max offset.
     */
    async alignDocument({ rootState }, documentId) {
        if (rootState?.forms?.align) {
            const witness =
                rootState.forms.align.textualWitnessType === "select"
                    ? { existingWitness: rootState.forms.align.textualWitness }
                    : { witnessFile: rootState.forms.align.textualWitnessFile };
            const beamOrOffset = rootState.forms.align.beamSize
                ? { beamSize: rootState.forms.align.beamSize }
                : { maxOffset: rootState.forms.align.maxOffset };
            await alignDocument({
                documentId,
                fullDoc: rootState.forms.align.fullDoc,
                gap: rootState.forms.align.gap,
                layerName: rootState.forms.align.layerName,
                merge: rootState.forms.align.merge,
                ngram: rootState.forms.align.ngram,
                regionTypes: rootState.forms.align.regionTypes,
                threshold: rootState.forms.align.threshold,
                transcription: rootState.forms.align.transcription,
                ...beamOrOffset,
                ...witness,
            });
        } else {
            throw new Error("Error: alignment failed, no form fields found");
        }
    },
    /**
     * Confirm cancelling a task and close the cancel warning modal.
     */
    async cancel({ commit, dispatch, state }, { documentId }) {
        try {
            commit(
                "document/setLoading",
                { key: "tasks", loading: true },
                { root: true },
            );
            await cancelTask({ documentId, taskReportId: state.selectedTask });
            dispatch("closeModal", "cancelWarning");
            commit(
                "document/setLoading",
                { key: "tasks", loading: false },
                { root: true },
            );
            // show toast alert on success
            dispatch(
                "alerts/add",
                {
                    color: "success",
                    message: "Task canceled successfully",
                },
                { root: true },
            );
        } catch (error) {
            commit(
                "document/setLoading",
                { key: "tasks", loading: false },
                { root: true },
            );
            dispatch("alerts/addError", error, { root: true });
        }
    },
    /**
     * Close the modal by key and clear its form.
     */
    closeModal({ commit, dispatch, rootState }, key) {
        commit("setModalOpen", { key, open: false });
        if (Object.hasOwnProperty.call(initialFormState, key)) {
            dispatch("forms/clearForm", key, { root: true });
            // when clearing forms with regionTypes, ensure default (all types selected)
            // is set if possible
            if (
                Object.hasOwnProperty.call(initialFormState[key], "regionTypes")
            ) {
                commit(
                    "forms/setFieldValue",
                    {
                        form: key,
                        field: "regionTypes",
                        value:
                            rootState?.document?.regionTypes?.map((rt) =>
                                rt.pk.toString(),
                            ) || [],
                    },
                    { root: true },
                );
            }
        }
    },
    /**
     * Queue the export task for a document.
     */
    async exportDocument({ rootState }, documentId) {
        await exportDocument({
            documentId,
            regionTypes: rootState?.forms?.export?.regionTypes,
            fileFormat: rootState?.forms?.export?.fileFormat,
            transcription: rootState?.forms?.export?.transcription,
            includeImages: rootState?.forms?.export?.includeImages,
        });
    },
    /**
     * Use the import form state to queue the import task for a document.
     */
    async importImagesOrTranscription({ rootState }, documentId) {
        let params = {};
        if (rootState?.forms?.import?.mode) {
            params["mode"] = rootState.forms.import.mode;
            switch (params["mode"]) {
                case "pdf":
                    params["upload_file"] = rootState.forms.import.uploadFile;
                    break;
                case "iiif":
                    params["iiif_uri"] = rootState.forms.import.iiifUri;
                    break;
                case "mets":
                    params["name"] = rootState.forms.import.layerName;
                    params["override"] = rootState.forms.import.overwrite;
                    params["mets_type"] = rootState.forms.import.metsType;
                    if (params["mets_type"] === "url") {
                        params["mets_uri"] = rootState.forms.import.metsUri;
                    } else {
                        params["upload_file"] =
                            rootState.forms.import.uploadFile;
                    }
                    break;
                case "xml":
                    params["name"] = rootState.forms.import.layerName;
                    params["override"] = rootState.forms.import.overwrite;
                    params["upload_file"] = rootState.forms.import.uploadFile;
                    break;
                // image files already uploaded to the /parts endpoint by the drop zone component,
                // so no need to do anything with them
                case "images":
                default:
                    return;
            }
            if (params["name"] && params["mode"] !== "mets") {
                // first, create a transcription layer by POSTing the name to the endpoint
                const { data } = await createTranscriptionLayer({
                    documentId,
                    layerName: params["name"],
                });
                // then, use the result to set the "transcription" param to new layer's pk
                if (data) {
                    params["transcription"] = data.pk;
                }
                delete params["name"];
            }
            return await queueImport({ documentId, params });
        }
    },
    /**
     * Open a task modal by key.
     */
    openModal({ commit }, key) {
        commit("setModalOpen", { key, open: true });
    },
    /**
     * Queue the segmentation task for a document.
     */
    async segmentDocument({ rootState }, documentId) {
        // segmentation steps should be "both", "regions", or "lines"
        const steps =
            rootState?.forms?.segment?.include?.length === 2
                ? "both"
                : rootState?.forms?.segment?.include[0];
        await segmentDocument({
            documentId,
            override: rootState?.forms?.segment?.overwrite,
            model: rootState?.forms?.segment?.model,
            steps,
        });
    },
    /**
     * Set the selected task pk on the state (e.g. for cancellation)
     */
    selectTask({ commit }, task) {
        commit("setSelectedTask", task.pk);
    },
    /**
     * Queue the transcription task for a document.
     */
    async transcribeDocument({ rootState }, documentId) {
        // first, create a transcription layer by POSTing the name to the endpoint
        const { data } = await createTranscriptionLayer({
            documentId,
            layerName: rootState.forms.transcribe.layerName,
        });
        // then, use the result to set the "transcription" param to new layer's pk
        if (data) {
            const transcription = data.pk;
            await transcribeDocument({
                documentId,
                model: rootState?.forms?.transcribe?.model,
                transcription,
            });
        } else {
            throw new Error("Unable to create transcription layer.");
        }
    },
};

const mutations = {
    setModalOpen(state, { key, open }) {
        state.modalOpen[key] = open;
    },
    setSelectedTask(state, task) {
        state.selectedTask = task;
    },
};

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations,
};
