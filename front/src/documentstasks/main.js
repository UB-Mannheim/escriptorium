import Vue from "vue";
import store from "./index.js";
import DocumentsTasks from "../../vue/components/DocumentsTasks/List.vue";

export var docstasksVM = new Vue({
    el: "#documents_tasks",
    store,
    components: {
        documentstasks: DocumentsTasks,
    },
});
