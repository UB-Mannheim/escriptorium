import store from "./index.js";
import Editor from "../../vue/components/Editor.vue";

export var partVM = new Vue({
    el: "#editor",
    store,
    components: {
        editor: Editor,
    },
});
