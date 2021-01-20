import { assign } from 'lodash'
import * as api from '../api'

export const initialState = () => ({
    lines: [],

    // internal
    masksToRecalc: [],
    debouncedRecalculateMasks: null,
    debouncedRecalculateOrdering: null
})

export const getters = {
    hasMasks: state => {
        return state.lines.findIndex(l=>l.mask!=null) != -1
    }
}

export const mutations = {
    setLines (state, lines) {
        assign(state.lines, lines.map(l => ({ ...l, loaded: true })))
    },
    appendLine (state, line) {
        state.lines.push({ ...line, loaded: false })
    },
    loadLine (state, pk) {
        let index = state.lines.findIndex(l => l.pk == pk)
        state.lines[index].loaded = true 
    },
    updateLine (state, line) {
        let index = state.lines.findIndex(l => l.pk == line.pk)
        state.lines[index].baseline =line.baseline
        state.lines[index].mask =line.mask
        state.lines[index].region =line.region
    },
    removeLine (state, index) {
        Vue.delete(state.lines, index)
    },
    updateLinesOrder (state, { lines, recalculate }) {
        for (let i=0; i<lines.length; i++) {
            let lineData = lines[i]
            let index = state.lines.findIndex(l => l.pk == lineData.pk)
            if (index != -1) {
                if (recalculate) {
                    state.lines[index] = { ...state.lines[index], order: i }
                } else {
                    state.lines[index] = { ...state.lines[index], order: lineData.order }
                }
            }
        }
    },
    updateLinesCurrentTrans (state, transcription) {
        state.lines = state.lines.map(line => {
            if (!line.transcriptions[transcription]) return line
            return { ...line, currentTrans: line.transcriptions[transcription] }
        })
    },
    setMasksToRecalc (state, value) {
        state.masksToRecalc = value
    },
    setLineTranscriptions (state, { pk, transcription }) {
        let index = state.lines.findIndex(l => l.pk == pk)
        if (index < 0) return
        let tr = state.lines[index].transcriptions || {}
        if (transcription) {
            tr[transcription.transcription] = transcription
            state.lines[index] = { ...state.lines[index], transcriptions: tr }
        }
        state.lines[index] = { ...state.lines[index], currentTrans: transcription }
    },
    createLineTranscriptions (state, createdTranscriptions) {
        for (let i=0; i<createdTranscriptions.lines.length; i++) {
            let lineTrans = createdTranscriptions.lines[i]
            let index = state.lines.findIndex(l => l.pk == lineTrans.line)
            if (index < 0) return
            state.lines[index] = {
                ...state.lines[index],
                currentTrans: { ...state.lines[index].currentTrans, pk: lineTrans.pk }
            }
        }
    },
    updateLineTranscriptionVersion (state, { pk, content }) {
        let index = state.lines.findIndex(l=>l.pk == pk)
        if (index < 0) return
        state.lines[index] = {
            ...state.lines[index],
            currentTrans: { ...state.lines[index].currentTrans, content: content }
        }
    },
    reset (state) {
        if (state.debouncedRecalculateMasks) {
            state.debouncedRecalculateMasks.flush()
        }
        if (state.debouncedRecalculateOrdering) {
            state.debouncedRecalculateOrdering.flush()
        }
        assign(state, initialState())
    }
}

export const actions = {
    async bulkCreateLines({commit, dispatch, getters, rootState}, {lines, transcription}) {
        lines.forEach(l=>l.document_part = rootState.parts.pk)

        const resp = await api.bulkCreateLines(rootState.parts.documentId, rootState.parts.pk, {lines: lines})

        let data = resp.data
        let createdLines = []
        for (let i=0; i<data.lines.length; i++) {
            let l = data.lines[i]
            let newLine = l
            newLine.currentTrans = {
                line: newLine.pk,
                transcription: transcription,
                content: '',
                versions: [],
                version_author: '',
                version_source: '',
                version_updated_at: null
            }
            createdLines.push(newLine)
            commit('appendLine', newLine)
        }

        await dispatch('recalculateOrdering')
        if (getters.hasMasks) {
            await dispatch('recalculateMasks', createdLines.map(l=>l.pk))
        }

        return createdLines
    },

    async bulkUpdateLines({state, commit, dispatch, getters, rootState}, lines) {
        let dataLines = lines.map(function(l) {
            let type  = l.type && rootState.parts.types.lines.find(t=>t.name==l.type)
            return {
                pk: l.pk,
                document_part: rootState.parts.pk,
                baseline: l.baseline,
                mask: l.mask,
                region: l.region,
                typology: type && type.pk || null
            }
        })

        const resp = await api.bulkUpdateLines(rootState.parts.documentId, rootState.parts.pk, {lines: dataLines})

        let data = resp.data
        let updatedLines = []
        let updatedBaselines = []
        for (let i=0; i<data.lines.length; i++) {
            let lineData = data.lines[i]
            let line = state.lines.find(function(l) {
                return l.pk==lineData.pk
            })
            if (line) {
                if (!_.isEqual(line.baseline, lineData.baseline)) {
                    updatedBaselines.push(line)
                }
                commit('updateLine', lineData)
                updatedLines.push(line)
            }
        }

        if (getters.hasMasks && updatedBaselines.length) {
            await dispatch('recalculateMasks', updatedBaselines.map(l=>l.pk))
        }

        return updatedLines
    },
    
    async bulkDeleteLines({state, dispatch, commit, rootState}, pks) {
        await api.bulkDeleteLines(rootState.parts.documentId, rootState.parts.pk, {lines: pks})
        
        let deletedLines = []
        for (let i=0; i<pks.length; i++) {
            let index = state.lines.findIndex(l=>l.pk==pks[i])
            if (index != -1) {
                deletedLines.push(pks[i])
                commit('removeLine', index)
            }
        }

        await dispatch('recalculateOrdering')

        return deletedLines
    },

    async moveLines({commit, rootState}, movedLines) {
        const resp = await api.moveLines(rootState.parts.documentId, rootState.parts.pk, {"lines": movedLines})
        let data = resp.data
        commit('updateLinesOrder', { lines: data, recalculate: false })
    },

    recalculateMasks({state, commit, rootState}, only=[]) {
        commit('setMasksToRecalc', _.uniq(state.masksToRecalc.concat(only)))
        if (!state.debouncedRecalculateMasks) {
            // avoid calling this too often
            state.debouncedRecalculateMasks = _.debounce(async function(only) {
                const params = {}
                if (state.masksToRecalc.length > 0) params.only = state.masksToRecalc.toString()
                commit('setMasksToRecalc', [])
                try {
                    await api.recalculateMasks(rootState.parts.documentId, rootState.parts.pk, {}, params)
                } catch (err) {
                    console.log('couldnt recalculate masks!', err)
                }
            }, 2000)
        }
        state.debouncedRecalculateMasks(only)
    },

    recalculateOrdering({state, commit, rootState}) {
        if (!state.debouncedRecalculateOrdering) {
            // avoid calling this too often
            state.debouncedRecalculateOrdering = _.debounce(async function() {
                try {
                    const resp = await api.recalculateOrdering(rootState.parts.documentId, rootState.parts.pk, {})
                    let data = resp.data
                    commit('updateLinesOrder', { lines: data.lines, recalculate: true })
                } catch (err) {
                    console.log('couldnt recalculate ordering!', err)
                }
            }, 1000)
        }
        state.debouncedRecalculateOrdering()
    },
}

export default {
    namespaced: true,
    state: initialState(),
    getters,
    mutations,
    actions
}