<template>
    <div
        id="tagsManagement"
        ref="tagsManagement"
        class="modal fade"
        tabindex="-1"
        role="dialog"
        aria-labelledby="tagsManagementLabel"
        aria-hidden="true"
    >
        <div
            id="modaltag"
            class="modal-dialog modal-dialog-centered modal-xl"
            role="document"
        >
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">
                        Tags management
                    </h5>
                    <button
                        type="button"
                        class="close"
                        data-dismiss="modal"
                        aria-label="Close"
                    >
                        <span aria-hidden="true">&times;</span>
                    </button>
                </div>
                <div
                    ref="formManageTag"
                    method="post"
                    action="#"
                >
                    <input
                        id="project-id"
                        v-model="projectIdComputed"
                        type="hidden"
                        class="form-control"
                        name="project"
                    >
                    <div class="modal-body row mb-0 pb-0">
                        <div class="form-group col-sm-4 d-inline-flex mx-auto">
                            <input
                                ref="tagName"
                                type="text"
                                class="form-control m-1"
                                placeholder="Type to add a tag"
                                @focusout="updateSingleTag()"
                            >
                            <input
                                ref="tagColor"
                                type="color"
                                class="form-control m-1 w-25"
                                :value="tagColor"
                                @focusout="updateSingleTag()"
                            >
                        </div>
                    </div>
                    <div class="modal-body row">
                        <div
                            v-for="tag in tags"
                            :id="'div-tag-' + tag.pk"
                            :key="tag.pk"
                            class="form-group col-sm-4 d-inline-flex"
                            :value="tag.pk"
                        >
                            <input
                                :id="'checkbox-tag-' + tag.pk"
                                type="checkbox"
                                title="Assign this tag to selected documents."
                                @click="assignSingleTag(tag.pk)"
                            >
                            <input
                                :id="'name-tag-' + tag.pk"
                                type="text"
                                class="form-control m-1"
                                :value="tag.name"
                                @focusout="updateSingleTag(tag.pk)"
                            >
                            <input
                                :id="'color-tag-' + tag.pk"
                                type="color"
                                class="form-control m-1 w-25"
                                :value="tag.color"
                                @focusout="updateSingleTag(tag.pk)"
                            >
                            <button
                                type="button"
                                class="btn btn-danger m-1"
                                @click="deleteSingleTag(tag.pk)"
                            >
                                <i class="fas fa-trash" />
                            </button>
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
        "projectId",
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
    watch: {
        "$store.state.documentslist.mapTags": {
            handler: function(nv) {
                this.tags = nv;
                this.$store.commit("documentslist/setTagColor");
            },
            immediate: true
        }
    },
    mounted(){
        $(this.$refs.tagsManagement).on("show.bs.modal", this.populateItems);
    },
    methods: {
        async updateSingleTag(pk=null){
            let _name = ($("#name-tag-" + pk).val()) ? $("#name-tag-" + pk).val() : $(this.$refs.tagName).val();
            if(_name){
                if(pk) await this.$store.dispatch("documentslist/updateProjectTag", {pk: pk, name: _name, color: $("#color-tag-" + pk).val()});
                else{
                    await this.$store.dispatch("documentslist/updateDocumentTags", {name: _name, color: $(this.$refs.tagColor).val()});
                    this.resetField();
                }
            }
        },
        async deleteSingleTag(pk){
            await this.$store.dispatch("documentslist/deleteProjectTag", {pk: pk});
            $("#div-tag-" + pk).remove();
        },
        async assignSingleTag(pk){
            await this.$store.dispatch("documentslist/assignSingleTagToDocuments", {pk: pk, selected: $("#checkbox-tag-" + pk).prop("checked")});
        },
        async populateItems(){
            this.$store.commit("documentslist/setProjectID", this.projectId);
            this.$store.commit("documentslist/setTagColor");
            await this.$store.dispatch("documentslist/getAllTagsProject");
        },
        resetField(){
            $(this.$refs.tagName).val("");
        }
    }
}
</script>

<style scoped>
</style>
