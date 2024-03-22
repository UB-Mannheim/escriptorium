// initial state
const state = () => ({
    /**
     * alerts: [{
     *     actionLabel?: String,
     *     actionLink?: String,
     *     color: String,
     *     count?: Number,
     *     delay?: Number,
     *     message: String,
     *     id: Number,
     * }]
     */
    alerts: [],
    // a counter of all alerts that have been created, to give each a unique id
    idCounter: 0,
});
const actions = {
    add({ _, commit }, alert) {
        commit("addAlert", alert);
    },
    /**
     * Helper function to reuse common logic for errors
     */
    async addError({ commit }, error) {
        const { response, message } = error;
        const url = response?.config?.baseURL + response?.config?.url;
        if (response?.status === 400) {
            Object.entries(response.data?.error || {}).forEach(
                ([key, value]) => {
                    if (key === "non_field_errors") {
                        commit("addAlert", {
                            color: "alert",
                            message: `Error: ${value}`,
                        });
                    } else {
                        commit("addAlert", {
                            color: "alert",
                            message: `Error for field ${key}: ${value}`,
                        });
                    }
                },
            );
        } else {
            commit("addAlert", {
                color: "alert",
                message:
                    (response?.data?.message || message) +
                    (url ? `: ${url}` : ""),
            });
        }
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
        const foundIndex = state.alerts.findIndex((a) => a.message === alert.message);
        if (foundIndex !== -1) {
            // if we already have an alert with this message, just update its count
            const foundAlert = state.alerts[foundIndex];
            foundAlert.count += 1;
            const alertsClone = structuredClone(state.alerts);
            alertsClone[foundIndex] = foundAlert;
        } else {
            // otherwise, add it, set its count to 1, and add 1 to idCounter
            state.alerts.push({ ...alert, id: state.idCounter, count: 1 });
            state.idCounter += 1;
        }

    },
    /**
     * Remove an alert from the list, by id.
     */
    removeAlert: (state, alert) => {
        const { id } = alert;
        if (id || id === 0) {
            const index = state.alerts.findIndex((a) => a.id === id);
            if (index !== -1) {
                state.alerts.splice(index, 1);
            }
        }
    },
};
export default {
    namespaced: true,
    state,
    actions,
    mutations,
};
