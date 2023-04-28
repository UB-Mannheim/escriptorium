import initialFormState from "../util/initialFormState";

const state = () => ({
    ...initialFormState,
});

const getters = {};

const actions = {
    /**
     * Handle text input generically
     */
    handleTextInput({ commit }, { form, field, value }) {
        commit("setFieldValue", { form, field, value });
    },
    /**
     * Clear form, resetting all fields to empty string and tags to empty array
     */
    clearForm({ commit }, form) {
        commit("setFormState", {
            form,
            formState: { ...initialFormState[form] },
        });
    },
    /**
     * Update the list of selected tags on the state.
     */
    handleTagsInput({ commit }, { form, checked, tag }) {
        if (checked) {
            commit("selectTag", { form, tag });
        } else {
            commit("deselectTag", { form, tag });
        }
    },
};

const mutations = {
    deselectTag(state, { form, tag }) {
        const formClone = structuredClone(state[form]);
        formClone.tags.splice(formClone.tags.indexOf(tag.pk), 1);
        state[form] = formClone;
    },
    selectTag(state, { form, tag }) {
        const formClone = structuredClone(state[form]);
        formClone.tags.push(tag.pk);
        state[form] = formClone;
    },
    setFieldValue(state, { form, field, value }) {
        const formClone = structuredClone(state[form]);
        formClone[field] = value;
        state[form] = formClone;
    },
    setFormState(state, { form, formState }) {
        state[form] = formState;
    },
};

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations,
};
