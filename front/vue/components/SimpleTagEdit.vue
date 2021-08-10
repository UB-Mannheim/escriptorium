<template>
    <a href="#"
        v-on:click="launchmodal"
        title="Manage tags"
        class="btn btn-info set-tag-meta btn-primary"
        data-toggle="modal"
        data-target="#tagsModal" 
        ref="tagedit">
        <i @click="launchmodal" class="fas fa fa-tags"></i>
    </a>
</template>

<script>

export default {
    props: [
        'documentId',
    ],
    methods: {
        async launchmodal(event){
            event.preventDefault();
            let document_id = $(this.$refs.tagedit).attr('document_id');
            this.$store.commit('documentslist/setDocumentID', document_id);
            await this.$store.dispatch('documentslist/getunlinktagbydocument', document_id);
        },
    }
}
</script>

<style scoped>
</style>
