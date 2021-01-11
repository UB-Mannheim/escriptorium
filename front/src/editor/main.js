window.Vue = require('vue/dist/vue');
import Editor from '../../vue/components/Editor.vue';

export var partVM = new Vue({
    el: "#editor",
    components: {
        'editor': Editor,
    }
});
