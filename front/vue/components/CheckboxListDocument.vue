<template>
    <input
        ref="checkbox"
        type="checkbox"
        class="checkbox-document-list"
        @click="appendDocument"
    >
</template>

<script>
export default {
    props: [
        "documentId",
    ],
    computed: {
        lastChecked() {
            return this.$store.state.documentslist.lastChecked;
        }
    },
    methods: {
        appendDocument(event){
            let id = parseInt($(this.$refs.checkbox).prop("id"));
            let checked = $(this.$refs.checkbox).prop("checked");
            let scope = this;
            scope.$store.commit("documentslist/setCheckboxList", {"selected": parseInt(this.documentId), "bool": checked});
            if (event.shiftKey) {
                if (this.lastChecked) {
                    let range = (id > this.lastChecked) ? new Array(this.lastChecked, id) : new Array(id, this.lastChecked);
                    $(".checkbox-document-list").each(function(i, obj) {
                        let item = $(this).prop("id");
                        if(parseInt(item) > range[0] && parseInt(item) < range[1]){
                            $(this).prop("checked", true);
                            scope.$store.commit("documentslist/setCheckboxList", {"selected": parseInt($(this).val()), "bool": true});
                        }
                    });
                }
            }
            scope.$store.commit("documentslist/setLastChecked", id);
        }
    }
}
</script>
