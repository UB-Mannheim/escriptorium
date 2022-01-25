import Vue from 'vue'
import Vuex from 'vuex'
import { assign } from 'lodash'
import * as api from './api.js'

Vue.use(Vuex)


const initialState = () => ({
    documentsTasks: {}
})

const mutations = {
    setDocumentsTasks(state, payload) {
        state.documentsTasks = assign({}, state.documentsTasks, payload)
    }
}

const actions = {
    async fetchDocumentsTasks({ commit }, page) {
        try {
            const resp = await api.listDocumentsTasks(page)
            let data = resp.data
            commit('setDocumentsTasks', data)
        } catch (err) {
            console.log('couldnt fetch documents tasks!', err)
        }
    }
}

export default new Vuex.Store({
    state: initialState(),
    mutations,
    actions
})
