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
});
const actions = {
    add({ _, commit }, alert) {
        commit("addAlert", alert);
    },
    /**
     * Helper function to handle errors in particular
     */
    addError({ commit }, error) {
        const { response, message } = error;
        commit("addAlert", {
            color: "alert",
            message: response?.data?.message || message,
        });
        console.error(error);
    },
    remove({ _, commit }, index) {
        commit("removeAlert", index);
    },
};
const mutations = {
    /**
     * Add an alert to the list, giving it an id of the highest id + 1;
     */
    addAlert: (state, alert) => {
        let id = 0;
        if (state.alerts.length) {
            const maxId = state.alerts.reduce((max, alert) =>
                max.id > alert.id ? max : alert,
            );
            id = maxId.id + 1;
        }
        state.alerts.push({ ...alert, id });
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
