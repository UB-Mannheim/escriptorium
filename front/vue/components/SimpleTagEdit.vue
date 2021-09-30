<template>
    <button type="button"
            v-on:click="launchModal"
            data-toggle="modal"
            data-target="#tagsModal"
            title="Manage tags"
            class="nav-item btn btn-sm btn-primary"><i class="fas fa fa-tags"></i></button>
</template>

<script>

export default {
    props: [
        'documentId',
    ],
    methods: {
        async launchModal(event){
            this.$store.commit('documentslist/setDocumentID', this.documentId);
            await this.$store.dispatch('documentslist/getUnlinkTagByDocument', this.documentId);
        },
    }
}
</script>

<style scoped>
</style>
