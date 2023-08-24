// initial state
const state = () => ({
    /**
     * alerts: [{
     *     color: String,
     *     message: String,
     *     id: Number,
     * }]
     */
    alerts: [],
    // a counter of all alerts that have been created, to give each a unique id
    count: 0,
});
const actions = {
    add({ _, commit }, alert) {
        commit("addAlert", alert);
    },
    /**
     * Helper function to reuse common logic for errors
     */
    addError({ commit }, error) {
        const { response, message } = error;
        const url = response?.config?.baseURL + response?.config?.url;
        commit("addAlert", {
            color: "alert",
            message:
                (response?.data?.message || message) + (url ? `: ${url}` : ""),
        });
        console.error(error);
    },
    remove({ _, commit }, index) {
        commit("removeAlert", index);
    },
};
const mutations = {
    /**
     * Add an alert to the list, giving it an id from the current counter
     */
    addAlert: (state, alert) => {
        state.alerts.push({ ...alert, id: state.count });
        state.count += 1;
    },
    /**
     * Remove an alert from the list, by id.
     */
    removeAlert: (state, alert) => {
        const { id } = alert;
        if (id || id === 0) {
            const index = state.alerts.findIndex((a) => a.id === id);
            state.alerts.splice(index, 1);
        }
    },
};
export default {
    namespaced: true,
    state,
    actions,
    mutations,
};
