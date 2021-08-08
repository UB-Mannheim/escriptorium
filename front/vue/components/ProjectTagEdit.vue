<template>
        <i @click="launchmodal" class="btn btn-info btn-sm fas fa fa-tags" data-toggle="modal" data-target="#tagsModal"></i>
</template>

<script>

export default {
    props: [
        'projectId',
    ],
    data () {
        return {
            projectid: 0
        }
    },
    computed: {
        iddoc() {
            return this.projectid;
        },
    },
    beforeCreate() {
        this.$nextTick(function () {
            this.projectid = this.projectId;
        })
    },
    methods: {
        async launchmodal(event){
            let document_id = event.target.getAttribute('project_id');
            this.$store.commit('documentslist/setProjectID', project_id);
            await this.$store.dispatch('documentslist/getunlinktagbydocument', project_id);
        },
    }
}
</script>

<style scoped>
</style>
