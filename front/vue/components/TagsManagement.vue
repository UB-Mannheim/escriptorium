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
                    <div class="modal-body row mb-0 pb-0">
                        <div class="form-group col-sm-4 d-inline-flex mx-auto">
                            <input type="text" class="form-control m-1" @focusout="updateSingleTag()" ref="tagName" placeholder="Add a new tag">
                            <input type="color" class="form-control m-1 w-25" v-bind:value="tagColor" @focusout="updateSingleTag()" ref="tagColor">
                        </div>
                    </div>
                    <div class="modal-body row">
                        <div class="form-group col-sm-4 d-inline-flex" v-for="tag in tags" :key="tag.pk" v-bind:value="tag.pk" v-bind:id="'div-tag-' + tag.pk">
                            <input type="checkbox" v-bind:id="'checkbox-tag-' + tag.pk" v-on:click="assignSingleTag(tag.pk)">
                            <input type="text" class="form-control m-1" v-bind:id="'name-tag-' + tag.pk" v-bind:value="tag.name" @focusout="updateSingleTag(tag.pk)">
                            <input type="color" class="form-control m-1 w-25" v-bind:id="'color-tag-' + tag.pk" v-bind:value="tag.color" @focusout="updateSingleTag(tag.pk)">
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
        async updateSingleTag(pk=null){
            let _name = ($("#name-tag-" + pk).val()) ? $("#name-tag-" + pk).val() : $(this.$refs.tagName).val();
            if(_name){
                if(pk) await this.$store.dispatch('documentslist/updateProjectTag', {pk: pk, name: _name, color: $("#color-tag-" + pk).val()});
                else{
                    await this.$store.dispatch('documentslist/updateDocumentTags', {name: _name, color: $(this.$refs.tagColor).val()});
                    this.resetField();
                }
            }
        },
        async deleteSingleTag(pk){
            await this.$store.dispatch('documentslist/deleteProjectTag', {pk: pk});
            $("#div-tag-" + pk).remove();
        },
        async assignSingleTag(pk){
            await this.$store.dispatch('documentslist/assignSingleTagToDocuments', {pk: pk, selected: $('#checkbox-tag-' + pk).prop('checked')});
        },
        async populateItems(){
            this.$store.commit('documentslist/setProjectID', this.projectId);
            this.$store.commit('documentslist/setTagColor');
            await this.$store.dispatch('documentslist/getAllTagsProject');
        },
        hideModal(){
            document.location.reload();
        },
        resetField(){
            $(this.$refs.tagName).val("");
        }
    },
    watch: {
        "$store.state.documentslist.mapTags": {
            handler: function(nv) {
                this.tags = nv;
                this.$store.commit('documentslist/setTagColor');
            },
            immediate: true 
        }
    }
}
</script>

<style scoped>
</style>



