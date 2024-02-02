import initialFormState from "../util/initialFormState";

const state = () => ({
    ...initialFormState,
});

const getters = {};

const actions = {
    /**
     * Handle text (or other) input generically
     */
    handleGenericInput({ commit }, { form, field, value }) {
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
            commit("addToArray", { form, field: "tags", value: tag.pk });
        } else {
            commit("removeFromArray", { form, field: "tags", value: tag.pk });
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
    /**
     * Take a checkbox input and translate it into array add/remove operations.
     */
    handleCheckboxArrayInput({ commit }, { form, field, checked, value }) {
        if (checked) {
            commit("addToArray", { form, field, value });
        } else {
            commit("removeFromArray", { form, field, value });
        }
    },
    /**
     * Handle array add/change/remove operations.
     */
    handleGenericArrayInput({ commit }, { form, field, action, value }) {
        switch (action) {
            case "add":
                commit("addToArray", { form, field, value });
                break;
            case "remove":
                commit("removeObjectFromArray", { form, field, value });
                break;
            case "update":
                commit("updateArrayValue", { form, field, value });
                break;
        }
    },
    /**
     * Show a named tooltip on a form
     */
    showTooltip({ commit }, { form, tooltip }) {
        commit("setTooltipShown", { form, tooltip, shown: true });
    },
    /**
     * Hide a named tooltip on a form
     */
    hideTooltip({ commit }, { form, tooltip }) {
        commit("setTooltipShown", { form, tooltip, shown: false });
    },
};

const mutations = {
    addToArray(state, { form, field, value }) {
        const formClone = structuredClone(state[form]);
        formClone[field].push(value);
        state[form] = formClone;
    },
    addMetadatum(state, { form, metadatum }) {
        const formClone = structuredClone(state[form]);
        formClone.metadata.push(metadatum);
        state[form] = formClone;
    },
    removeFromArray(state, { form, field, value }) {
        const formClone = structuredClone(state[form]);
        formClone[field].splice(formClone[field].indexOf(value), 1);
        state[form] = formClone;
    },
    removeObjectFromArray(state, { form, field, value }) {
        const formClone = structuredClone(state[form]);
        const foundIndex = formClone[field].findIndex(
            (v) =>
            // use pk if it exists on the backend, otherwise use index
                (value.pk && v.pk.toString() === value.pk.toString()) ||
                (value.index && v.index === value.index),
        );
        // remove if found
        if (foundIndex !== -1) {
            formClone[field].splice(foundIndex, 1);
            state[form] = formClone;
        }
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
    updateArrayValue(state, { form, field, value }) {
        const formClone = structuredClone(state[form]);
        const foundIndex = formClone[field].findIndex(
            (v) =>
            // use pk if it exists on the backend, otherwise use index
                (value.pk && v.pk.toString() === value.pk.toString()) ||
                (value.index && v.index === value.index),
        );
        // update if found
        if (foundIndex !== -1) {
            formClone[field][foundIndex] = value;
            state[form] = formClone;
        }
    },
    setTooltipShown(state, { form, tooltip, shown }) {
        const formClone = structuredClone(state[form]);
        formClone.tooltipShown[tooltip] = shown;
        state[form] = formClone;
    },
};

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations,
};
