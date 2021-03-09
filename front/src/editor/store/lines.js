import { assign } from 'lodash'
import * as api from '../api'

export const initialState = () => ({
    all: [],
    editedLine: null,
    // internal
    masksToRecalc: [],
    debouncedRecalculateMasks: null,
    debouncedRecalculateOrdering: null
})

export const getters = {
    hasMasks: state => {
        return state.all.findIndex(l=>l.mask!=null) != -1
    }
}

export const mutations = {
    set (state, lines) {
        assign(state.all, lines.map(l => ({ ...l, loaded: true })))
    },
    append (state, line) {
        state.all.push({ ...line, loaded: false })

        // Force reference update on the whole array
        // so that all components get a full refresh after an update
        state.all = [...state.all]
    },
    load (state, pk) {
        let index = state.all.findIndex(l => l.pk == pk)
        state.all[index].loaded = true
    },
    update (state, line) {
        let index = state.all.findIndex(l => l.pk == line.pk)
        if (line.baseline !== undefined)
            state.all[index].baseline = line.baseline
        if (line.mask !== undefined)
            state.all[index].mask = line.mask
        if (line.region !== undefined)
            state.all[index].region = line.region

        // Force reference update on the whole array
        // so that all components get a full refresh after an update
        state.all = [...state.all]
    },
    remove (state, index) {
        Vue.delete(state.all, index)

        // Force reference update on the whole array
        // so that all components get a full refresh after an update
        state.all = [...state.all]
    },
    setEditedLine (state, line) {
        state.editedLine = line
    },
    updateOrder (state, { lines, recalculate }) {
        for (let i=0; i<lines.length; i++) {
            let lineData = lines[i]
            let index = state.all.findIndex(l => l.pk == lineData.pk)
            if (index != -1) {
                if (recalculate) {
                    state.all[index].order = i
                } else {
                    state.all[index].order = lineData.order
                }
            }
        }
        state.all = [...state.all.sort((a, b) => (a.order > b.order) ? 1 : -1)]
    },
    updateCurrentTrans (state, transcription) {
        state.all = state.all.map(line => {
            if (!line.transcriptions[transcription]) return line
            return { ...line, currentTrans: line.transcriptions[transcription] }
        })
    },
    setMasksToRecalc (state, value) {
        state.masksToRecalc = value
    },
    setTranscriptions (state, { pk, transcription }) {
        let index = state.all.findIndex(l => l.pk == pk)
        if (index < 0) return
        let tr = state.all[index].transcriptions || {}
        if (transcription) {
            tr[transcription.transcription] = transcription
            state.all[index] = { ...state.all[index], transcriptions: tr }
        }
        // Force reference update on the whole array
        // so that all components get a full refresh after an update
        state.all = [...state.all]
    },
    createTranscriptions (state, createdTranscriptions) {
        for (let i=0; i<createdTranscriptions.lines.length; i++) {
            let lineTrans = createdTranscriptions.lines[i]
            let index = state.all.findIndex(l => l.pk == lineTrans.line)
            if (index < 0) return
            state.all[index] = {
                ...state.all[index],
                currentTrans: { ...state.all[index].currentTrans, pk: lineTrans.pk },
                transcriptions: {
                    ...state.all[index].transcriptions,
                    [lineTrans.transcription]: {
                        ...state.all[index].transcriptions[lineTrans.transcription],
                        pk: lineTrans.pk
                    }
                }
            }
        }
        // Force reference update on the whole array
        // so that all components get a full refresh after an update
        state.all = [...state.all]
    },
    updateTranscriptionVersion (state, { pk, content }) {
        let index = state.all.findIndex(l=>l.pk == pk)
        if (index < 0) return
        state.all[index] = {
            ...state.all[index],
            currentTrans: { ...state.all[index].currentTrans, content: content }
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
    async bulkCreate({commit, dispatch, getters, rootState}, {lines, transcription}) {
        lines.forEach(l=>l.document_part = rootState.parts.pk)

        const resp = await api.bulkCreateLines(rootState.document.id, rootState.parts.pk, {lines: lines})

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
            commit('append', newLine)
        }

        await dispatch('recalculateOrdering')
        if (getters.hasMasks) {
            await dispatch('recalculateMasks', createdLines.map(l=>l.pk))
        }

        return createdLines
    },

    async bulkUpdate({state, commit, dispatch, getters, rootState}, lines) {
        let dataLines = lines.map(function(l) {
            let type  = l.type && rootState.document.types.lines.find(t=>t.name==l.type)
            return {
                pk: l.pk,
                document_part: rootState.parts.pk,
                baseline: l.baseline,
                mask: l.mask,
                region: l.region,
                typology: type && type.pk || null
            }
        })

        const resp = await api.bulkUpdateLines(rootState.document.id, rootState.parts.pk, {lines: dataLines})

        let data = resp.data
        let updatedLines = []
        let updatedBaselines = []
        let hasToRecalculateOrdering = false
        for (let i=0; i<data.lines.length; i++) {
            let lineData = data.lines[i]
            let line = state.all.find(function(l) {
                return l.pk==lineData.pk
            })
            if (line) {
                if (!_.isEqual(line.baseline, lineData.baseline)) {
                    updatedBaselines.push(line)
                }
                if (line.region != lineData.region) hasToRecalculateOrdering = true
                commit('update', lineData)
                updatedLines.push(line)
            }
        }

        if (getters.hasMasks && updatedBaselines.length) {
            await dispatch('recalculateMasks', updatedBaselines.map(l=>l.pk))
        }
        if (hasToRecalculateOrdering) {
            await dispatch('recalculateOrdering')
        }

        return updatedLines
    },

    async bulkDelete({state, dispatch, commit, rootState}, pks) {
        await api.bulkDeleteLines(rootState.document.id, rootState.parts.pk, {lines: pks})

        let deletedLines = []
        for (let i=0; i<pks.length; i++) {
            let index = state.all.findIndex(l=>l.pk==pks[i])
            if (index != -1) {
                deletedLines.push(pks[i])
                commit('remove', index)
            }
        }

        await dispatch('recalculateOrdering')

        return deletedLines
    },

    async move({commit, rootState}, movedLines) {
        const resp = await api.moveLines(rootState.document.id, rootState.parts.pk, {"lines": movedLines})
        let data = resp.data
        commit('updateOrder', { lines: data, recalculate: false })
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
                    await api.recalculateMasks(rootState.document.id, rootState.parts.pk, {}, params)
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
                    const resp = await api.recalculateOrdering(rootState.document.id, rootState.parts.pk, {})
                    let data = resp.data
                    commit('updateOrder', { lines: data.lines, recalculate: true })
                } catch (err) {
                    console.log('couldnt recalculate ordering!', err)
                }
            }, 1000)
        }
        state.debouncedRecalculateOrdering()
    },

    toggleLineEdition({commit}, line) {
        commit('setEditedLine', line)
    },

    editLine({state, commit}, direction) {
        if (direction == 'next') {
            let index = state.all.findIndex(l => l.pk == state.editedLine.pk)
            if (index < state.all.length - 1) {
                commit('setEditedLine', state.all[index + 1])
            }
        } else {
            let index = state.all.findIndex(l => l.pk == state.editedLine.pk)
            if (index >= 1) {
                commit('setEditedLine', state.all[index - 1])
            }
        }
    }
}

export default {
    namespaced: true,
    state: initialState(),
    getters,
    mutations,
    actions
}
