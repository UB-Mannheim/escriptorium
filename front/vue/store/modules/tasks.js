import { segmentDocument } from "../../../src/api";

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
     * Close the modal by key and clear its form.
     */
    closeModal({ commit, dispatch }, key) {
        commit("setModalOpen", { key, open: false });
        dispatch("forms/clearForm", key, { root: true });
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
