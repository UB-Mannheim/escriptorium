// initial state
const state = () => ({
    category: "regions",
    modalOpen: false,
    // ontology: [{
    //    pk: Number,
    //    name: String,
    //    count: Number,
    // }],
    ontology: [],
    sortState: {},
});

const getters = {};

const actions = {};

const mutations = {
    setCategory(state, category) {
        state.category = category;
    },
    setOntology(state, ontology) {
        state.ontology = ontology;
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
