import { assign } from 'lodash'
import * as api from '../api'

export const initialState = () => ({
    regions: []
})

export const mutations = {
    setRegions (state, regions) {
        assign(state.regions, regions.map(r => ({ ...r, loaded: true })))
    },
    appendRegion (state, region) {
        state.regions.push({ ...region, loaded: false })
    },
    loadRegion (state, pk) {
        let index = state.regions.findIndex(l => l.pk == pk)
        state.regions[index].loaded = true 
    },
    updateRegion (state, { pk, region }) {
        let index = state.regions.findIndex(r=>r.pk==pk)
        if (index < 0) return
        state.regions[index].box = region.box
    },
    removeRegion (state, pk) {
        let index = state.regions.findIndex(r=>r.pk==pk)
        if (index < 0) return
        Vue.delete(state.regions, index)
    },
    reset (state) {
        assign(state, initialState())
    }
}

export const actions = {
    async createRegion({commit, rootState}, region) {
        let type = region.type && rootState.parts.types.regions.find(t=>t.name==region.type)
        let data = {
            document_part: rootState.parts.pk,
            typology: type && type.pk || null,
            box: region.box
        }

        const resp = await api.createRegion(rootState.parts.documentId, rootState.parts.pk, data)

        let newRegion = resp.data
        commit('appendRegion', newRegion)

        return newRegion
    },

    async updateRegion({commit, rootState}, region) {
        let type = region.type && rootState.parts.types.regions.find(t=>t.name==region.type)
        let data = {
            document_part: rootState.parts.pk,
            box: region.box,
            typology: type && type.pk || null
        }

        const resp = await api.updateRegion(rootState.parts.documentId, rootState.parts.pk, region.pk, data)
        let updatedRegion = resp.data
        commit('updateRegion', { pk: region.pk, region: updatedRegion })

        return updatedRegion
    },

    async deleteRegion({commit, rootState}, regionPk) {
        await api.deleteRegion(rootState.parts.documentId, rootState.parts.pk, regionPk)
        
        commit('removeRegion', regionPk)
    }
}

export default {
    namespaced: true,
    state: initialState(),
    mutations,
    actions
}