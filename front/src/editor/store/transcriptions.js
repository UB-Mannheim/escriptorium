import { assign } from 'lodash'
import * as api from '../api'

export const initialState = () => ({
    transcriptions: []
})

export const mutations = {
    setTranscriptions (state, transcriptions) {
        assign(state.transcriptions, transcriptions)
    },
    removeTranscription (state, pk) {
        let index = state.transcriptions.findIndex(t=>t.pk==pk)
        if (index < 0) return
        Vue.delete(state.transcriptions, index)
    },
    reset (state) {
        assign(state, initialState())
    }
}

export const actions = {
    async bulkCreateLineTranscriptions({commit, rootState}, transcriptions) {
        let data = transcriptions.map(l=>{
            return {
                line : l.line,
                transcription : l.transcription,
                content : l.content
            }
        })

        try {
            const resp = await api.bulkCreateLineTranscriptions(rootState.parts.documentId, rootState.parts.pk, {lines: data})
            let createdTrans = resp.data
            commit('lines/createLineTranscriptions', createdTrans, {root: true})
        } catch (err) {
            console.log('couldnt create transcription lines', err)
        }
    },

    async bulkUpdateLineTranscriptions({rootState}, transcriptions) {
        let data = transcriptions.map(l => {
            return {
                pk: l.pk,
                content: l.content,
                line : l.line,
                transcription : l.transcription
            }
        })

        try {
            await api.bulkUpdateLineTranscriptions(rootState.parts.documentId, rootState.parts.pk, {lines: data})
            // No store update ????
        } catch (err) {
            console.log('couldnt update transcription lines', err)
        }
    },

    async fetchContent({commit, rootState}, transcription) {
        // first create a default transcription for every line
        rootState.lines.lines.forEach(function(line) {
            const tr = {
                line: line.pk,
                transcription: transcription,
                content: '',
                version_author: null,
                version_source: null,
                version_updated_at: null
            }
            commit('lines/setLineTranscriptions', { pk: line.pk, transcription: tr }, {root: true})
        })

        //  then fetch all content page by page
        let fetchPage = async function(page) {
            const resp = await api.retrievePage(rootState.parts.documentId, rootState.parts.pk, transcription, page)
            
            let data = resp.data
            for (var i=0; i<data.results.length; i++) {
                let line = rootState.lines.lines.find(l=>l.pk == data.results[i].line)
                commit('lines/setLineTranscriptions', { pk: line.pk, transcription: data.results[i] }, {root: true})
            }
            if (data.next) fetchPage(page+1)
        }
        await fetchPage(1)
    },

    async updateLineTranscriptionVersion({commit, dispatch, rootState}, {line, content}) {
        commit('lines/updateLineTranscriptionVersion', { pk: line.pk, content: content }, {root: true})
        
        const l = rootState.lines.lines.find(li=>li.pk == line.pk)
        let data = {
            content: l.currentTrans.content,
            line: l.currentTrans.line,
            transcription: l.currentTrans.transcription
        }

        if (l.currentTrans.pk) {
            await dispatch('updateContent', {pk: l.currentTrans.pk, content: data, currentTransLine: l.currentTrans.line})
        } else {
            await dispatch('createContent', {content: data, currentTransLine: l.currentTrans.line})
        }
    },

    async createContent({commit, rootState}, {content, currentTransLine}) {
        try {
            const resp = await api.createContent(rootState.parts.documentId, rootState.parts.pk, content)
            commit('lines/setLineTranscriptions', { pk: currentTransLine, transcription: resp.data }, {root: true})
        } catch (err) {
            console.log('couldnt create transcription!', err);
        }
    },

    async updateContent({commit, rootState}, {pk, content, currentTransLine}) {
        try {
            const resp = await api.updateContent(rootState.parts.documentId, rootState.parts.pk, pk, content)
            commit('lines/setLineTranscriptions', { pk: currentTransLine, transcription: resp.data }, {root: true})
        } catch (err) {
            console.log('couldnt update transcription!', err);
        }
    },

    async archiveTranscription({commit, rootState}, transPk) {
        try {
            await api.archiveTranscription(rootState.parts.documentId, transPk)
            commit('removeTranscription', transPk)
        } catch (err) {
            console.log('couldnt archive transcription #', transPk, err)
        }
    },
}

export default {
    namespaced: true,
    state: initialState(),
    mutations,
    actions
}