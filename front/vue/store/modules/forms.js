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
    /**
     * Update the list of metadata items on the state.
     */
    handleMetadataInput({ commit }, { form, action, metadatum }) {
        switch (action) {
            case "add":
                commit("addMetadatum", { form, metadatum });
                break;
            case "remove":
                commit("removeMetadatum", { form, metadatum });
                break;
            case "update":
                commit("updateMetadatum", { form, metadatum });
                break;
        }
    },
};

const mutations = {
    addMetadatum(state, { form, metadatum }) {
        const formClone = structuredClone(state[form]);
        formClone.metadata.push(metadatum);
        state[form] = formClone;
    },
    deselectTag(state, { form, tag }) {
        const formClone = structuredClone(state[form]);
        formClone.tags.splice(formClone.tags.indexOf(tag.pk), 1);
        state[form] = formClone;
    },
    removeMetadatum(state, { form, metadatum }) {
        const formClone = structuredClone(state[form]);
        const foundIndex = formClone.metadata.findIndex(
            (m) =>
                // use pk if it exists on the backend, otherwise use index
                (metadatum.pk && m.pk.toString() === metadatum.pk.toString()) ||
                (metadatum.index && m.index === metadatum.index),
        );
        // remove if found
        if (foundIndex !== -1) {
            formClone.metadata.splice(foundIndex, 1);
            state[form] = formClone;
        }
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
    updateMetadatum(state, { form, metadatum }) {
        const formClone = structuredClone(state[form]);
        const foundIndex = formClone.metadata.findIndex(
            (m) =>
                // use pk if it exists on the backend, otherwise use index
                (metadatum.pk && m.pk.toString() === metadatum.pk.toString()) ||
                (metadatum.index && m.index === metadatum.index),
        );
        // update if found
        if (foundIndex !== -1) {
            formClone.metadata[foundIndex] = metadatum;
            state[form] = formClone;
        }
    },
};

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations,
};
