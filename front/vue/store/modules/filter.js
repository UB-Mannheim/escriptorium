// initial state
const state = () => ({
    /**
     * filters: [{
     *     type: String,
     *     value: String | Array,
     *     operator?: Boolean,
     * }]
     */
    filters: [],
});

const getters = {
    /**
     * Number of tags currently selected in the tag filter.
     */
    tagCount: (_, getters) => {
        return getters.tagFilterSelectedTags?.length;
    },
    /**
     * The tag filter object from the list of filters.
     */
    tagFilter: (state) => {
        return state.filters.find((filter) => filter.type === "tags");
    },
    /**
     * Boolean indicating whether there is a tag filter in the current list of filters.
     */
    tagFilterActive: (state) => {
        return state.filters.some((filter) => filter.type === "tags");
    },
    /**
     * AND or OR operator currently applied to tag filter.
     */
    tagFilterOperator: (_, getters) => {
        return getters.tagFilter?.operator;
    },
    /**
     * Tags currently selected in the tag filter.
     */
    tagFilterSelectedTags: (_, getters) => {
        return getters.tagFilter?.value;
    },
    /**
     * Whether or not "untagged" is checked in the current tag filter.
     */
    untaggedSelected: (state) => {
        return state.filters
            .find((filter) => filter.type === "tags")
            ?.value?.includes("none");
    },
};

const actions = {
    addFilter({ _, commit }, params) {
        commit("addFilter", params);
    },
    removeFilter({ _, commit }, params) {
        commit("removeFilter", params);
    },
};

const mutations = {
    /**
     * Add a filter to the list.
     */
    addFilter: (state, filter) => {
        const filters = state.filters.filter((f) => f.type !== filter.type);
        filters.push(filter);
        state.filters = filters;
    },
    /**
     * Remove a filter from the list.
     */
    removeFilter: (state, type) => {
        state.filters = state.filters.filter((f) => f.type !== type);
    },
};

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations,
};
