import { retrieveElementsByType, retrievePartsByChar } from "../../../src/api";

// initial state
const state = () => ({
    category: "regions",
    loading: false,
    modalOpen: false,
    // ontology: [{
    //    pk: Number,
    //    name: String,
    //    count: Number,
    // }],
    ontology: [],
    sortState: {},
    // map of "category-typePk" (typePk or "none") to { loading, parts }
    partsByType: {},
    // map of character to { loading, parts }
    partsByChar: {},
});

const getters = {};

const actions = {
    /**
     * Fetch the parts that contain a given type, for the ontology overview page.
     */
    async fetchElementsByType({ commit, rootState }, { category, typePk }) {
        const key = `${category}-${typePk ?? "none"}`;
        commit("setPartsByTypeLoading", { key, loading: true });
        try {
            const { data } = await retrieveElementsByType({
                documentId: rootState.document.id,
                category,
                typePk,
            });
            commit("setPartsByType", { key, parts: data.parts });
        } finally {
            commit("setPartsByTypeLoading", { key, loading: false });
        }
    },
    /**
     * Fetch the parts that contain a given character, for the ontology overview page.
     */
    async fetchPartsByChar({ commit, rootState }, { char, transcriptionId }) {
        commit("setPartsByCharLoading", { char, loading: true });
        try {
            const { data } = await retrievePartsByChar({
                documentId: rootState.document.id,
                transcriptionId,
                char,
            });
            commit("setPartsByChar", { char, parts: data.parts });
        } finally {
            commit("setPartsByCharLoading", { char, loading: false });
        }
    },
};

const mutations = {
    setCategory(state, category) {
        state.category = category;
    },
    setOntology(state, ontology) {
        state.ontology = ontology;
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
    setPartsByType(state, { key, parts }) {
        state.partsByType = {
            ...state.partsByType,
            [key]: { ...state.partsByType[key], parts },
        };
    },
    setPartsByTypeLoading(state, { key, loading }) {
        state.partsByType = {
            ...state.partsByType,
            [key]: { ...state.partsByType[key], loading },
        };
    },
    setPartsByChar(state, { char, parts }) {
        state.partsByChar = {
            ...state.partsByChar,
            [char]: { ...state.partsByChar[char], parts },
        };
    },
    setPartsByCharLoading(state, { char, loading }) {
        state.partsByChar = {
            ...state.partsByChar,
            [char]: { ...state.partsByChar[char], loading },
        };
    },
};

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations,
};
