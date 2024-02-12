import { assign } from "lodash";
import * as api from "../api";

export const initialState = () => ({
    all: [],
});

export const mutations = {
    set(state, annotations) {
        assign(
            state.all,
            annotations.map((r) => ({ ...r, loaded: true })),
        );
    },
    append(state, annotation) {
        state.all.push({ ...annotation, loaded: false });
    },
    load(state, pk) {
        let index = state.all.findIndex((l) => l.pk == pk);
        state.all[index].loaded = true;
    },
    /* update (state, { pk, annotation }) {
     *     let index = state.all.findIndex(a=>a.pk==pk)
     *     if (index < 0) return
     * }, */
    remove(state, pk) {
        let index = state.all.findIndex((a) => a.pk == pk);
        if (index < 0) return;
        Vue.delete(state.all, index);
    },
    reset(state) {
        assign(state, initialState());
    },
};

export const actions = {
    async fetch({ commit, dispatch, rootState }) {
        commit("reset");
        let next = true,
            page = 1;
        let data = [];
        while (next != null) {
            let resp = await api.retrieveImageAnnotations(
                rootState.document.id,
                rootState.parts.pk,
                page,
            );

            page = page + 1;
            data.push(...resp.data.results);
            next = resp.data.next;
        }
        commit("set", data);
        return data;
    },

    async create({ commit, rootState }, annotation) {
        const resp = await api.createImageAnnotation(
            rootState.document.id,
            rootState.parts.pk,
            annotation,
        );
        let newAnnotation = resp.data;

        commit("append", newAnnotation);

        return newAnnotation;
    },

    async update({ commit, rootState }, annotation) {
        const resp = await api.updateImageAnnotation(
            rootState.document.id,
            rootState.parts.pk,
            annotation.id,
            annotation,
        );
        return resp.data;
    },

    async delete({ commit, rootState }, annotationPk) {
        const resp = await api.deleteImageAnnotation(
            rootState.document.id,
            rootState.parts.pk,
            annotationPk,
        );
        commit("remove", annotationPk);
    },
};

export default {
    namespaced: true,
    state: initialState(),
    mutations,
    actions,
};
