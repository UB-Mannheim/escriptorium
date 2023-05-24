import {
    alignDocument,
    exportDocument,
    segmentDocument,
    transcribeDocument,
} from "../../../src/api";

// initial state
const state = () => ({
    modalOpen: {
        align: false,
        export: false,
        import: false,
        overwriteWarning: false,
        segment: false,
        transcribe: false,
    },
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
     * Close the modal by key and clear its form.
     */
    closeModal({ commit, dispatch }, key) {
        commit("setModalOpen", { key, open: false });
        dispatch("forms/clearForm", key, { root: true });
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
     * Queue the transcription task for a document.
     */
    async transcribeDocument({ rootState }, documentId) {
        await transcribeDocument({
            documentId,
            model: rootState?.forms?.transcribe?.model,
            layerName: rootState?.forms?.transcribe?.layerName,
        });
    },
};

const mutations = {
    setModalOpen(state, { key, open }) {
        state.modalOpen[key] = open;
    },
};

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations,
};
