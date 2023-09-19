const state = () => ({
    /**
     * characters: [{
     *    char: String,
     *    frequency: Number,
     * }]
     */
    characters: [],
    loading: false,
    modalOpen: false,
    /**
     * sortState: {
     *    direction: Number,
     *    field: String,
     * }
     */
    sortState: {
        direction: 1,
        field: "char",
    },
});

const getters = {};

const actions = {};

const mutations = {
    setCharacters(state, characters) {
        state.characters = characters;
    },
    setLoading(state, loading) {
        state.loading = loading;
    },
    setModalOpen(state, open) {
        state.modalOpen = open;
    },
    setSortState(state, sortState) {
        state.sortState = sortState;
    },
};

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations,
};
