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
})

export const mutations = {
    setPartPk (state, pk) {
        state.pk = pk
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
    async fetchPart ({commit, dispatch, rootState}, pk) {
        commit('setPartPk', pk)
        if (!rootState.transcriptions.all.length) {
            await dispatch('document/fetchDocument', rootState.document.id, {root: true})
        }
        const resp = await api.retrieveDocumentPart(rootState.document.id, pk)
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

    async rotate({state, commit, dispatch, rootState}, angle) {
        await api.rotateDocumentPart(rootState.document.id, state.pk, {angle: angle})

        let pk = state.pk
        commit('regions/reset', {}, {root: true})
        commit('lines/reset', {}, {root: true})
        commit('reset')
        await dispatch('fetchPart', pk)
    },

    async loadPart({state, commit, dispatch, rootState}, direction) {
        if (!state.loaded || !state[direction]) return
        let part = state[direction]
        commit('regions/reset', {}, {root: true})
        commit('lines/reset', {}, {root: true})
        commit('reset')
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
