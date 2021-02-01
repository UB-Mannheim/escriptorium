import { assign } from 'lodash'
import * as api from '../api'

export const initialState = () => ({
    documentId: null,
    pk: null,
    loaded: false,
    previous: null,
    next: null,
    image: {},
    bw_image: {},
    filename: '',
    name: '',
    title: '',
    types: {},
    recoverable: null,
    transcription_progress: null,
    typology: null,
    workflow: {},
})

export const mutations = {
    setDocumentId (state, id) {
        state.documentId = id
    },
    setPartPk (state, pk) {
        state.pk = pk
    },
    setTypes (state, types) {
        state.types = types
    },
    load (state, part) {
        assign(state, part)
        state.loaded = true
    },
    reset (state) {
        assign(state, initialState())
    }
}

export const actions = {
    async fetchDocument ({state, commit}) {
        const resp = await api.retrieveDocument(state.documentId)
        let data = resp.data
        commit('transcriptions/set', data.transcriptions, {root: true})
        commit('setTypes', { 'regions': data.valid_block_types, 'lines': data.valid_line_types })
    },

    async fetchPart ({state, commit, dispatch, rootState}, pk) {
        commit('setPartPk', pk)
        if (!rootState.transcriptions.all.length) {
            await dispatch('fetchDocument', state.documentId)
        }
        const resp = await api.retrieveDocumentPart(state.documentId, pk)
        let data = resp.data
        
        data.lines.forEach(function(line) {
            let type_ = line.typology && state.types.lines.find(t=>t.pk == line.typology)
            line.type = type_ && type_.name
        })
        commit('lines/set', data.lines, {root: true})
        delete data.lines

        data.regions.forEach(function(reg) {
            let type_ = reg.typology && state.types.regions.find(t=>t.pk == reg.typology)
            reg.type = type_ && type_.name
        })
        commit('regions/set', data.regions, {root: true})
        delete data.regions

        commit('load', data)
    },

    async rotate({state, commit, dispatch}, angle) {
        await api.rotateDocumentPart(state.documentId, state.pk, {angle: angle})

        let pk = state.pk
        let documentId = state.documentId
        commit('regions/reset', {}, {root: true})
        commit('lines/reset', {}, {root: true})
        commit('reset')
        commit('setDocumentId', documentId)
        await dispatch('fetchPart', pk)
    },

    async loadPart({state, commit, dispatch, rootState}, direction) {
        if (!state.loaded || !state[direction]) return
        let documentId = state.documentId
        let part = state[direction]
        commit('regions/reset', {}, {root: true})
        commit('lines/reset', {}, {root: true})
        commit('reset')
        commit('setDocumentId', documentId)
        try {
            await dispatch('fetchPart', part)
            await dispatch('transcriptions/getCurrentContent', rootState.transcriptions.selectedTranscription, {root: true})
            await dispatch('transcriptions/getComparisonContent', {}, {root: true})
        } catch (err) {
            console.log('couldnt fetch part data!', err)
        }
    },
}

export default {
    namespaced: true,
    state: initialState(),
    mutations,
    actions
}