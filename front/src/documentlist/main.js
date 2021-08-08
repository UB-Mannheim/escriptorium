import Vue from 'vue'
import store from '../editor/index';
import TagsSelector from '../../vue/components/TagsSelector.vue';
import SimpleTagEdit from '../../vue/components/SimpleTagEdit.vue';
import TagsModal from '../../vue/components/TagsModal.vue';
import ChecboxListDocument from '../../vue/components/ChecboxListDocument.vue';

export var doclistVM = new Vue({
    el: "#document_list",
    store,
    components: {
        'tagsselector': TagsSelector,
        'simpletagedit': SimpleTagEdit,
        'tagsmodal': TagsModal,
        'checboxlistdocument': ChecboxListDocument,
    }
});
