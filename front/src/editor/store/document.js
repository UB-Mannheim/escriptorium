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

    // Confidence overlay visibility
    confidenceVisible: false,
    // exponential scale factor for confidence overlay
    confidenceScale: 4,

    enabledVKs: userProfile.get('VK-enabled')? userProfile.get('VK-enabled'):[]
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
        state.visible_panels = Object.assign({}, state.visible_panels, payload)
    },
    setAnnotationTaxonomies(state, {type, taxos}) {
        state.annotationTaxonomies[type] = taxos
    },
    setEnabledVKs(state, vks) {
        state.enabledVKs = Object.assign([], state.enabledVKs, vks)
    },
    setConfidenceScale(state, scale) {
        state.confidenceScale = scale;
    },
    setConfidenceVizGloballyEnabled(state, enabled) {
        state.confidenceVisible = enabled;
    },
    reset (state) {
        Object.assign(state, initialState())
    }
}

export const actions = {
    async fetchDocument ({state, commit}) {
        const resp = await api.retrieveDocument(state.id)
        let data = resp.data
        commit('transcriptions/set', data.transcriptions, {root: true})
        commit('setTypes', { 'regions': data.valid_block_types, 'lines': data.valid_line_types })
        commit('setPartsCount', data.parts_count)
        commit('setConfidenceVizGloballyEnabled', data.show_confidence_viz)

        let page=1;
        var img_taxos = [];
        while(page) {
            let resp = await api.retrieveAnnotationTaxonomies(data.pk, 'image', page)
            img_taxos = img_taxos.concat(resp.data.results)
            if (resp.data.next) page++
            else page=null
        }
        commit('setAnnotationTaxonomies', {'type': 'image', 'taxos': img_taxos})

        page=1;
        var text_taxos = [];
        while(page) {
            let resp = await api.retrieveAnnotationTaxonomies(data.pk, 'text', page)
            text_taxos = text_taxos.concat(resp.data.results)
            if (resp.data.next) page++
            else page=null
        }
        commit('setAnnotationTaxonomies', {'type': 'text', 'taxos': text_taxos})
    },

    async togglePanel ({state, commit}, panel) {
        // Toggle the display of a single panel
        let update = {}
        update[panel] = !state.visible_panels[panel]
        commit('setVisiblePanels', update)

        // Persist final value in user profile
        userProfile.set('visible-panels', state.visible_panels)
    },

    async scaleConfidence({ commit }, scale) {
        commit('setConfidenceScale', scale);
    }
}

export default {
    namespaced: true,
    state: initialState(),
    mutations,
    actions
}
