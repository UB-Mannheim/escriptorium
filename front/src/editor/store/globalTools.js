const state = () => ({
    /** should be one of:
     *  select (global)
     *  pan (global)
     *  cut - splitting tool (segmentation)
     *  add-lines - drawing lines tool (segmentation)
     *  add-regions - drawing regions tool (segmentation)
     */
    activeTool: "select",
});

const getters = {};

const actions = {
    setActiveTool({ commit, state }, tool) {
        if (tool !== state.activeTool) {
            commit("setActiveTool", tool);
        }
    },
    toggleTool({ commit, state }, tool) {
        if (tool === state.activeTool) {
            commit("setActiveTool", "select");
        } else {
            commit("setActiveTool", tool);
        }
    },
};

const mutations = {
    setActiveTool(state, activeTool) {
        state.activeTool = activeTool;
    },
};

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations,
};
