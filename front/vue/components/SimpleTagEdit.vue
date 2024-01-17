<template>
    <button
        type="button"
        data-toggle="modal"
        data-target="#tagsModal"
        title="Assign tags"
        class="nav-item btn btn-sm btn-primary"
        @click="launchModal"
    >
        <i class="fas fa fa-tags" />
    </button>
</template>

<script>

export default {
    props: [
        "documentId",
    ],
    methods: {
        async launchModal(event){
            this.$store.commit("documentslist/setDocumentID", this.documentId);
            await this.$store.dispatch("documentslist/getUnlinkTagByDocument", this.documentId);
        },
    }
}
</script>

<style scoped>
</style>
