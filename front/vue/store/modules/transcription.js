// initial state
const state = () => ({
    characterCount: null,
    lineCount: null,
    loading: {
        characterCount: true,
    },
    selectedTranscription: null,
});

const getters = {};

const actions = {};

const mutations = {
    setCharacterCount(state, characterCount) {
        state.characterCount = characterCount;
    },
    setLineCount(state, lineCount) {
        state.lineCount = lineCount;
    },
    setLoading(state, { key, loading }) {
        state.loading[key] = loading;
    },
    setSelectedTranscription(state, transcriptionId) {
        state.selectedTranscription = transcriptionId;
    },
};

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations,
};
