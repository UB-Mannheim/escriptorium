import Vue from 'vue'
import Vuex from 'vuex'
import document from './store/document'
import parts from './store/parts'
import lines from './store/lines'
import regions from './store/regions'
import transcriptions from './store/transcriptions'
import documentslist from './store/documentslist'

Vue.use(Vuex)

export default new Vuex.Store({
    modules: {
        document,
        parts,
        lines,
        regions,
        transcriptions,
        documentslist,
    }
})