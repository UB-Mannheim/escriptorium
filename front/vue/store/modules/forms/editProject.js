const state = () => ({
    guidelines: "",
    name: "",
    tags: [],
    tagName: "",
});

const getters = {};

const actions = {
    /**
     * Set the project name on the state.
     */
    handleNameInput({ commit }, e) {
        commit("setName", e.target.value);
    },
    /**
     * Set the project guidelines on the state.
     */
    handleGuidelinesInput({ commit }, e) {
        commit("setGuidelines", e.target.value);
    },
    /**
     * Update the list of selected tags on the state.
     */
    handleTagsInput({ commit }, { checked, tag }) {
        if (checked) {
            commit("selectTag", tag);
        } else {
            commit("deselectTag", tag);
        }
    },
    /**
     * Set the tag name on the state.
     */
    handleTagNameInput({ commit }, e) {
        commit("setTagName", e.target.value);
    },
};

const mutations = {
    clearForm(state) {
        state.guidelines = "";
        state.name = "";
        state.tags = [];
        state.tagName = "";
    },
    deselectTag(state, tag) {
        state.tags.splice(state.tags.indexOf(tag.pk), 1);
    },
    selectTag(state, tag) {
        state.tags.push(tag.pk);
    },
    setGuidelines(state, guidelines) {
        state.guidelines = guidelines;
    },
    setName(state, name) {
        state.name = name;
    },
    setTagName(state, name) {
        state.tagName = name;
    },
    setTags(state, tags) {
        state.tags = tags;
    },
};

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations,
};
