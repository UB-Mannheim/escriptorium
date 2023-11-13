const state = () => ({
    /** should be one of:
     *  select (global)
     *  pan (global)
     *  cut - splitting tool (segmentation)
     *  add-lines - drawing lines tool (segmentation)
     *  add-regions - drawing regions tool (segmentation)
     */
    activeTool: "select",
    modalOpen: {
        deleteTranscription: false,
        elementDetails: false,
        models: false,
        ontology: false,
        transcriptions: false,
    },
});

const getters = {};

const actions = {
    /**
     * Close the "element details" modal and reset form state.
     */
    closeElementDetailsModal({ commit, rootState }) {
        commit("setModalOpen", { key: "elementDetails", open: false });
        commit(
            "forms/setFormState",
            {
                form: "elementDetails",
                formState: {
                    comments: rootState.parts.comments,
                    metadata: rootState.parts.metadata,
                    name: rootState.parts.name,
                    typology: rootState.parts.typology,
                },
            },
            { root: true },
        );
        // re-allow keyboard shortcuts
        commit("document/setBlockShortcuts", false, { root: true });
    },
    /**
     * Close the ontology modal and reset form state.
     */
    closeOntologyModal({ commit, rootState }) {
        commit("setModalOpen", { key: "ontology", open: false });
        commit(
            "forms/setFormState",
            {
                form: "ontology",
                formState: { ...rootState.document.types },
            },
            { root: true },
        );
        // re-allow keyboard shortcuts
        commit("document/setBlockShortcuts", false, { root: true });
    },
    /**
     * Close the transcriptions modal and reset form state.
     */
    closeTranscriptionsModal({ commit, rootState }) {
        commit("setModalOpen", { key: "transcriptions", open: false });
        commit("document/setBlockShortcuts", false, { root: true });
        commit(
            "forms/setFormState",
            {
                form: "transcriptionManagement",
                formState: {
                    transcriptions: rootState.transcriptions.all,
                },
            },
            { root: true },
        );
    },
    /**
     * Open an editor modal by key.
     */
    openModal({ commit }, key) {
        commit("setModalOpen", { key, open: true });
        // prevent keyboard shortcuts
        commit("document/setBlockShortcuts", true, { root: true });
    },
    /**
     * Set the currently active tool in the editor by name.
     */
    setActiveTool({ commit }, tool) {
        commit("setActiveTool", tool);
    },
    /**
     * Toggle the currently active tool in the editor by name.
     */
    toggleTool({ commit, state }, tool) {
        if (tool === state.activeTool) {
            commit("setActiveTool", "select");
        } else {
            commit("setActiveTool", tool);
        }
    },
};

const mutations = {
    setActiveTool(state, activeTool) {
        state.activeTool = activeTool;
    },
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
