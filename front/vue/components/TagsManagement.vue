<template>
    <div class="modal fade" id="tagsManagement" ref="tagsManagement" tabindex="-1" role="dialog" aria-labelledby="tagsManagementLabel" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered modal-xl" id="modaltag" role="document">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Tags management</h5>
                    <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                        <span aria-hidden="true">&times;</span>
                    </button>
                </div>
                <div method="post" action="#" ref="formManageTag">
                    <input type="hidden" class="form-control" id="project-id" name="project" v-model="projectIdComputed">
                    <div class="modal-body row">
                        <div class="form-group col-sm-4 d-inline-flex tag-template" v-for="tag in tags" :key="tag.pk" v-bind:value="tag.pk" v-bind:id="'div-tag-' + tag.pk">
                            <input type="text" class="form-control m-1" v-bind:id="'name-tag-' + tag.pk" v-bind:value="tag.name">
                            <input type="color" class="form-control m-1" v-bind:id="'color-tag-' + tag.pk" style="width: 20%;" v-bind:value="tag.color">
                            <button type="button" class="btn btn-primary m-1" v-on:click="updateSingleTag(tag.pk)"><i class="fas fa-save"></i></button>
                            <button type="button" class="btn btn-danger m-1" v-on:click="deleteSingleTag(tag.pk)"><i class="fas fa-trash"></i></button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
export default {
    props: [
        'projectId',
    ],
    data () {
        return {
            tags: []
        }
    },
    computed: {
        projectIdComputed() {
            return this.projectId
        },
        tagColor() {
            return this.$store.state.documentslist.tagColor;
        }
    },
    mounted(){
        $(this.$refs.tagsManagement).on("show.bs.modal", this.populateItems);
        $(this.$refs.tagsManagement).on("hide.bs.modal", this.hideModal);
    },
    methods: {
        async updateSingleTag(pk){
            let jsonData = {pk: pk, name: $("#name-tag-" + pk).val(), color: $("#color-tag-" + pk).val()};
            await this.$store.dispatch('documentslist/updateProjectTag', jsonData);
        },
        async deleteSingleTag(pk){
            await this.$store.dispatch('documentslist/deleteProjectTag', {pk: pk});
            $("#div-tag-" + pk).remove();
        },
        async populateItems(){
            this.$store.commit('documentslist/setProjectID', this.projectId);
            this.$store.commit('documentslist/settagColor');
            await this.$store.dispatch('documentslist/getAllTagsProject');
        },
        async hideModal(){
            document.location.reload();
        }
    },
    watch: {
        "$store.state.documentslist.mapTags": {
            handler: function(nv) {
                this.tags = nv;
                this.$nextTick(function(){ 
                });
            },
            immediate: true 
        }
    }
}
</script>

<style scoped>
</style>



