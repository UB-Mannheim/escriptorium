// initial state
const state = () => ({
    selectedAction: "",
});

const actions = {
    /**
     * Select the chosen action, or deselect the action if it's the current one.
     */
    toggleAction({ commit, state }, key) {
        if (key === state.selectedAction) {
            commit("setSelectedAction", "");
        } else {
            commit("setSelectedAction", key);
        }
    },
    /**
     * Close the sidebar, no matter the selected action
     */
    closeSidebar({ commit }) {
        commit("setSelectedAction", "");
    },
};

const mutations = {
    setSelectedAction(state, action) {
        state.selectedAction = action;
    },
};

export default {
    namespaced: true,
    state,
    actions,
    mutations,
};
