import { assign } from "lodash";
import * as api from "../api";

export const initialState = () => ({
    all: [],
});

export const mutations = {
    set(state, regions) {
        assign(
            state.all,
            regions.map((r) => ({ ...r, loaded: true })),
        );
    },
    append(state, region) {
        state.all.push({ ...region, loaded: false });
    },
    load(state, pk) {
        let index = state.all.findIndex((l) => l.pk == pk);
        state.all[index].loaded = true;
    },
    update(state, { pk, region }) {
        let index = state.all.findIndex((r) => r.pk == pk);
        if (index < 0) return;
        const clone = structuredClone(state.all);
        clone[index] = region;
        state.all = [...clone];
    },
    remove(state, pk) {
        let index = state.all.findIndex((r) => r.pk == pk);
        if (index < 0) return;
        Vue.delete(state.all, index);
    },
    reset(state) {
        assign(state, initialState());
    },
};

export const actions = {
    async create({ commit, rootState }, region) {
        let type =
            region.type &&
            rootState.document.types.regions.find((t) => t.name == region.type);
        let data = {
            document_part: rootState.parts.pk,
            typology: (type && type.pk) || null,
            box: region.box,
        };

        const resp = await api.createRegion(
            rootState.document.id,
            rootState.parts.pk,
            data,
        );

        let newRegion = resp.data;
        commit("append", newRegion);

        return newRegion;
    },

    async update({ commit, rootState }, region) {
        let type =
            region.type &&
            rootState.document.types.regions.find((t) => t.name == region.type);
        let data = {
            document_part: rootState.parts.pk,
            box: region.box,
            typology: (type && type.pk) || null,
        };

        const resp = await api.updateRegion(
            rootState.document.id,
            rootState.parts.pk,
            region.pk,
            data,
        );
        let updatedRegion = resp.data;
        commit("update", {
            pk: region.pk,
            region: { ...updatedRegion, type: type?.name },
        });

        return updatedRegion;
    },

    async delete({ commit, rootState }, regionPk) {
        await api.deleteRegion(
            rootState.document.id,
            rootState.parts.pk,
            regionPk,
        );

        commit("remove", regionPk);
    },
};

export default {
    namespaced: true,
    state: initialState(),
    mutations,
    actions,
};
