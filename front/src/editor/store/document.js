import { assign } from 'lodash'
import * as api from '../api'

export const initialState = () => ({
    id: null,
    name: "",
    defaultTextDirection: null,
    mainTextDirection: null,
    readDirection: null,
    types: {},
    blockShortcuts: false,

    // Manage panels visibility through booleans
    // Those values are initially populated by localStorage
    visible_panels: {
        source: userProfile.get('source-panel'),
        segmentation: userProfile.get('segmentation-panel'),
        visualisation: userProfile.get('visualisation-panel'),
        diplomatic: userProfile.get('diplomatic-panel')
    },
})

export const mutations = {
    setId (state, id) {
        state.id = id
    },
    setName (state, name) {
        state.name = name
    },
    setDefaultTextDirection (state, direction) {
        state.defaultTextDirection = direction
    },
    setMainTextDirection (state, direction) {
        state.mainTextDirection = direction
    },
    setReadDirection (state, direction) {
        state.readDirection = direction
    },
    setTypes (state, types) {
        state.types = types
    },
    setBlockShortcuts(state, block) {
        state.blockShortcuts = block
    },
    setVisiblePanels(state, payload) {
        state.visible_panels = assign({}, state.visible_panels, payload)
    },
    reset (state) {
        assign(state, initialState())
    }
}

export const actions = {
    async fetchDocument ({state, commit}) {
        const resp = await api.retrieveDocument(state.id)
        let data = resp.data
        commit('transcriptions/set', data.transcriptions, {root: true})
        commit('setTypes', { 'regions': data.valid_block_types, 'lines': data.valid_line_types })
    },

    async togglePanel ({state, commit}, panel) {
        // Toggle the display of a single panel
        let update = {}
        update[panel] = !state.visible_panels[panel]
        commit('setVisiblePanels', update)

        // Persist final value in user profile
        userProfile.set(panel + '-panel', state.visible_panels[panel])
    }
}

export default {
    namespaced: true,
    state: initialState(),
    mutations,
    actions
}
