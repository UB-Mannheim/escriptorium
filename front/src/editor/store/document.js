import * as api from '../api'

export const initialState = () => ({
    id: null,
    name: "",
    partsCount: 0,
    defaultTextDirection: null,
    mainTextDirection: null,
    readDirection: null,
    types: {},
    blockShortcuts: false,

    annotationTaxonomies: {},

    // Manage panels visibility through booleans
    // Those values are initially populated by localStorage
    visible_panels: {
        source: userProfile.get('visible-panels')?userProfile.get('visible-panels').source:false,
        segmentation: userProfile.get('visible-panels')?userProfile.get('visible-panels').segmentation:true,
        visualisation: userProfile.get('visible-panels')?userProfile.get('visible-panels').visualisation:true,
        diplomatic: userProfile.get('visible-panels')?userProfile.get('visible-panels').diplomatic:false
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
    setPartsCount(state, count) {
        state.partsCount = count
    },
    setBlockShortcuts(state, block) {
        state.blockShortcuts = block
    },
    setVisiblePanels(state, payload) {
        state.visible_panels = assign({}, state.visible_panels, payload)
    },
    setAnnotationTaxonomies(state, payload) {
        state.annotationTaxonomies[payload[0]] = payload[1]
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
        commit('setPartsCount', data.parts_count)

        // pagination?!
        // commit can not pass parameters as is?!?
        const img_taxos = await api.retrieveAnnotationTaxonomies(data.pk, 'image')
        commit('setAnnotationTaxonomies', ['image', img_taxos.data.results])
        const text_taxos = await api.retrieveAnnotationTaxonomies(data.pk, 'text')
        commit('setAnnotationTaxonomies', ['text', text_taxos.data.results])
    },

    async togglePanel ({state, commit}, panel) {
        // Toggle the display of a single panel
        let update = {}
        update[panel] = !state.visible_panels[panel]
        commit('setVisiblePanels', update)

        // Persist final value in user profile
        userProfile.set('visible-panels', state.visible_panels)
    }
}

export default {
    namespaced: true,
    state: initialState(),
    mutations,
    actions
}
