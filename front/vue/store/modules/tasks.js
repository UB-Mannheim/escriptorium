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
    closeModal({ commit }, key) {
        commit("setModalOpen", { key, open: false });
    },
    openModal({ commit }, key) {
        commit("setModalOpen", { key, open: true });
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
