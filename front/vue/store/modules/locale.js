import { setLanguage as setRuntimeLanguage } from "../../../src/translations/index.js";

export default {
    namespaced: true,
    state: () => ({
        current: "en",
        available: ["en", "fr", "de"],
    }),
    mutations: {
        SET_LANGUAGE(state, code) {
            if (state.available.includes(code)) {
                state.current = code;
            }
        },
    },
    actions: {
        setLanguage({ commit }, code) {
            setRuntimeLanguage(code);
            commit("SET_LANGUAGE", code);
        },
    },
};
