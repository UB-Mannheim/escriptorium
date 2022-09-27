import { assign } from 'lodash'
import * as api from '../api'

export const initialState = () => ({
    pk: null,
    loaded: false,
    previous: null,
    next: null,
    image: {},
    bw_image: {},
    filename: '',
    name: '',
    title: '',
    recoverable: null,
    transcription_progress: null,
    typology: null,
    workflow: {},
    metadata: null,
    typologies: null,
    comments: null
})

export const mutations = {
    setPartPk (state, pk) {
        state.pk = pk
    },
    load (state, part) {
        assign(state, part)
        state.loaded = true
    },
    setMetadata(state, metadata) {
        state.metadata = metadata
    },
    reset (state) {
        assign(state, initialState())
    }
}

export const actions = {
    async fetchPart ({commit, dispatch, rootState}, {pk, order}) {
        if (!rootState.transcriptions.all.length) {
            await dispatch('document/fetchDocument', rootState.document.id, {root: true})
        }
        var resp
        if (pk) {
            commit('setPartPk', pk)
            resp = await api.retrieveDocumentPart(rootState.document.id, pk)
        } else {
            resp = await api.retrieveDocumentPartByOrder(rootState.document.id, order)
            commit('setPartPk', resp.data.pk)
        }

        let data = resp.data

        data.lines.forEach(function(line) {
            let type_ = line.typology && rootState.document.types.lines.find(t=>t.pk == line.typology)
            line.type = type_ && type_.name
        })
        commit('lines/set', data.lines, {root: true})
        delete data.lines

        data.regions.forEach(function(reg) {
            let type_ = reg.typology && rootState.document.types.regions.find(t=>t.pk == reg.typology)
            reg.type = type_ && type_.name
        })
        commit('regions/set', data.regions, {root: true})
        delete data.regions

        commit('load', data)
    },

    async updatePart({state, commit, dispatch, rootState}, data) {
        const resp = await api.updatePart(rootState.document.id, state.pk, data)
        commit('load', resp.data)
    },

    async rotate({state, commit, dispatch, rootState}, angle) {
        await api.rotateDocumentPart(rootState.document.id, state.pk, {angle: angle})

        let pk = state.pk
        commit('regions/reset', {}, {root: true})
        commit('lines/reset', {}, {root: true})
        commit('imageAnnotations/reset', {}, {root: true})
        commit('textAnnotations/reset', {}, {root: true})
        commit('reset')
        await dispatch('fetchPart', {pk: pk})
    },

    async loadPartByOrder({state, commit, dispatch, rootState}, order) {
        commit('regions/reset', {}, {root: true})
        commit('lines/reset', {}, {root: true})
        commit('imageAnnotations/reset', {}, {root: true})
        commit('textAnnotations/reset', {}, {root: true})
        commit('reset')
        try {
            await dispatch('fetchPart', {order: order})
            await dispatch('transcriptions/getCurrentContent', rootState.transcriptions.selectedTranscription, {root: true})
            await dispatch('transcriptions/getComparisonContent', {}, {root: true})
        } catch (err) {
            console.log('couldnt fetch part data!', err)
        }
    },

    async loadPart({state, commit, dispatch, rootState}, direction) {
        if (!state.loaded || !state[direction]) return
        let part = state[direction]
        commit('regions/reset', {}, {root: true})
        commit('lines/reset', {}, {root: true})
        commit('imageAnnotations/reset', {}, {root: true})
        commit('textAnnotations/reset', {}, {root: true})
        commit('reset')
        try {
            await dispatch('fetchPart', {pk: part})
            await dispatch('transcriptions/getCurrentContent', rootState.transcriptions.selectedTranscription, {root: true})
            await dispatch('transcriptions/getComparisonContent', {}, {root: true})
        } catch (err) {
            console.log('couldnt fetch part data!', err)
        }
    },
    async createPartMetadata({state, commit, rootState}, data) {
        await api.createPartMetadata(rootState.document.id, state.pk, data)
        const resp = await api.retrievePartMetadata(rootState.document.id, state.pk)
        commit('setMetadata', resp.data.results)
    },
    async updatePartMetadata({state, commit, rootState}, {pk, data}) {
        await api.updatePartMetadata(rootState.document.id, state.pk, pk, data)
    },
    async deletePartMetadata({state, commit, rootState}, rowPk) {
        await api.deletePartMetadata(rootState.document.id, state.pk, rowPk)
        var metadata = state.metadata;
        const idx = metadata.findIndex(md => md.id == rowPk);
        metadata.splice(idx, 1);
    },
}

export default {
    namespaced: true,
    state: initialState(),
    mutations,
    actions
}
