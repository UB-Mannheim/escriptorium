import {
    availableLanguages,
    setLanguage as setRuntimeLanguage,
} from "../../../src/translations/index.js";

export default {
    namespaced: true,
    state: () => ({
        current: "en",
        available: Object.keys(availableLanguages),
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
            return setRuntimeLanguage(code).then(() => {
                commit("SET_LANGUAGE", code);
            });
        },
    },
};
