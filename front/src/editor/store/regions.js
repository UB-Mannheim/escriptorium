import { assign } from "lodash";
import * as api from "../api";

export const initialState = () => ({
    all: [],
    selectedPk: null,
    // bumped on every setSelected call, so re-selecting the same pk (e.g. clicking the
    // same row twice in the Elements panel) still re-triggers selection on the canvas,
    // even though it gets purged in between by clicks outside the canvas/toolbar
    selectedToken: 0,
    // last locked/unlocked region, as { pk, locked }, so SegPanel can sync it onto
    // the live Segmenter region; always a new object so the watcher fires every time
    lockUpdate: null,
});

export const mutations = {
    setSelected(state, pk) {
        state.selectedPk = pk;
        state.selectedToken++;
    },
    setLocked(state, { pk, locked }) {
        let index = state.all.findIndex((r) => r.pk == pk);
        if (index >= 0) {
            const clone = structuredClone(state.all);
            clone[index] = { ...clone[index], locked };
            state.all = [...clone];
        }
        state.lockUpdate = { pk, locked };
    },
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

    async update({ commit, rootState, state }, region) {
        let type =
            region.type &&
            rootState.document.types.regions.find((t) => t.name == region.type);
        // this is a full PUT, so we need to pass through the current locked state
        // explicitly or it would be reset to its default (false) by the API
        const current = state.all.find((r) => r.pk == region.pk);
        let data = {
            document_part: rootState.parts.pk,
            box: region.box,
            typology: (type && type.pk) || null,
            locked: region.locked ?? current?.locked ?? false,
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

    async toggleLocked({ commit, rootState, state }, pk) {
        const region = state.all.find((r) => r.pk == pk);
        const locked = !region?.locked;
        await api.updateRegionLocked(
            rootState.document.id,
            rootState.parts.pk,
            pk,
            locked,
        );
        commit("setLocked", { pk, locked });
    },
};

export default {
    namespaced: true,
    state: initialState(),
    mutations,
    actions,
};
