// initial state
const state = () => ({
    /**
     * filters: [{
     *     type: String,
     *     value: any,
     * }]
     */
    filters: [],
});

const getters = {
    /**
     * WIP for getting filtered documents on the frontend.
     */
    filteredDocuments: (state, getters, rootState) => {
        const conditions = [];
        state.filters.forEach((filter) => {
            switch (filter.type) {
                case "tags":
                    if (filter.value?.operator === "or") {
                        conditions.push((doc) =>
                            filter.value?.tags?.some((tag) =>
                                doc.tags.includes(tag),
                            ),
                        );
                    } else {
                        conditions.push((doc) =>
                            filter.value?.tags?.every((tag) =>
                                doc.tags.includes(tag),
                            ),
                        );
                    }
                    if (filter.value?.withoutTag) {
                        conditions.push((doc) => !doc.tags?.length);
                    }
                    break;
            }
        });
        return rootState.documents.filter((document) => {
            return conditions.every(
                (condition) => condition(document) === true,
            );
        });
    },
    /**
     * Tags currently selected in the tag filter.
     */
    selectedTags: (_, getters) => {
        return getters.tagFilter?.value?.tags;
    },
    /**
     * Number of tags currently selected in the tag filter.
     */
    tagCount: (_, getters) => {
        return getters.selectedTags?.length;
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
        return getters.tagFilter?.value?.operator;
    },
    /**
     * Whether or not "without tag" is checked in the current tag filter.
     */
    withoutTagSelected: (_, getters) => {
        return getters.tagFilter?.value?.withoutTag;
    },
};

const actions = {};

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
