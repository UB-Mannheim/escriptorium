import Vue from 'vue'
import Vuex from 'vuex'
import document from './store/document'
import parts from './store/parts'
import lines from './store/lines'
import regions from './store/regions'
import transcriptions from './store/transcriptions'
import taxonomies from './store/taxonomies'
import imageAnnotations from './store/image_annotations'
import textAnnotations from './store/image_annotations'
import documentslist from './store/documentslist'

Vue.use(Vuex)

export default new Vuex.Store({
    modules: {
        document,
        parts,
        lines,
        regions,
        transcriptions,
        taxonomies,
        imageAnnotations,
        textAnnotations,
        documentslist,
    }
})
