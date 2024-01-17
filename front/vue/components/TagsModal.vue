<template>
    <div
        id="tagsModal"
        ref="tagsModal"
        class="modal fade"
        tabindex="-1"
        role="dialog"
        aria-labelledby="tagsModalLabel"
        aria-hidden="true"
    >
        <div
            id="modaltag"
            class="modal-dialog modal-dialog-centered modal-md"
            role="document"
        >
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">
                        Assign tags
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
                <form
                    id="formTag"
                    ref="formTag"
                    method="post"
                    action="#"
                >
                    <div class="modal-body">
                        <input
                            id="project-id"
                            v-model="projectIdComputed"
                            type="hidden"
                            class="form-control"
                            name="project"
                        >
                        <input
                            id="document-id"
                            v-model="documentId"
                            type="hidden"
                            class="form-control"
                            name="document"
                        >
                        <input
                            id="valuesSelected"
                            v-model="valuesSelected"
                            type="hidden"
                            class="form-control"
                            name="selectedtags"
                        >
                        <input
                            id="checkboxlist"
                            v-model="checkboxListData"
                            type="hidden"
                            class="form-control"
                            name="checkboxlist"
                        >
                        <div class="form-row form-group justify-content-center">
                            <select
                                id="mselect-tags"
                                ref="mselectTags"
                                v-model="valuesSelected"
                                name="tags"
                                data-live-search="true"
                                data-live-search-placeholder="filters"
                                multiple
                            >
                                <option
                                    v-for="tag in tags"
                                    :key="tag.pk"
                                    :value="tag.pk"
                                >
                                    {{ tag.name }}
                                </option>
                            </select>
                        </div>
                        <div class="form-row form-group justify-content-center">
                            <input
                                ref="nameNewTag"
                                type="text"
                                class="form-control w-50"
                                name="name"
                                placeholder="Type to add a tag"
                            >
                            <input
                                v-model="rColor"
                                type="color"
                                class="form-control"
                                name="color"
                                style="width: 10%;"
                            >
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button
                            type="button"
                            class="btn btn-secondary"
                            data-dismiss="modal"
                        >
                            Close
                        </button>
                        <button
                            type="button"
                            class="btn btn-primary"
                            @click="updateTagList"
                        >
                            Save
                        </button>
                    </div>
                </form>
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
            valuesSelected: [],
            rColor: null,
            tags: []
        }
    },
    computed: {
        documentId() {
            return this.$store.state.documentslist.documentID;
        },
        listCheckedTags() {
            return this.$store.state.documentslist.checkedTags;
        },
        projectIdComputed() {
            return this.projectId;
        },
        checkboxListData() {
            return this.$store.state.documentslist.checkboxList;
        },
        randomColor() {
            return this.$store.state.documentslist.tagColor;
        }
    },
    watch: {
        "$store.state.documentslist.checkedTags": {
            handler: function(nv) {
                this.$nextTick(function(){
                    this.$store.commit("documentslist/setTagColor");
                    this.valuesSelected = nv;
                    $(this.$refs.mselectTags).selectpicker("val", nv);
                    $(this.$refs.mselectTags).selectpicker("refresh");
                    this.rColor = this.randomColor;
                });
            },
            immediate: true
        },
        "$store.state.documentslist.mapTags": {
            handler: function(nv) {
                this.tags = nv;
            },
            immediate: true
        }
    },
    mounted(){
        $(this.$refs.tagsModal).on("hide.bs.modal", this.hideModal);
        $(this.$refs.tagsModal).on("show.bs.modal", this.populateItems);
        this.$store.commit("documentslist/setTagColor");
    },
    updated: function(){
        this.$nextTick(function(){
            $(this.$refs.mselectTags).selectpicker({
                liveSearch: true,
                size: "auto",
                width: "auto"
            });
        });
    },
    methods: {
        async updateTagList(){
            let json_data = this.buildJSONData($(this.$refs.formTag)[0].elements);
            await this.$store.dispatch("documentslist/updateDocumentTags", json_data);
            $(this.$refs.tagsModal).modal("hide");
        },
        buildJSONData(el){
            let element = {};
            let tabindex = [];
            for(let i = 0; i < el.length; i++){
                if((el[i].value.toLowerCase() != "button") && (el[i].value.toLowerCase() != "submit")){
                    if(!tabindex.includes(el[i].name.toString())){
                        Object.defineProperty(element, el[i].name, { value: el[i].value });
                    }
                    tabindex.push(el[i].name.toString());
                }
            }
            return element;
        },
        hideModal(){
            this.$store.commit("documentslist/setDocumentID", null);
        },
        populateItems(){
            this.$store.commit("documentslist/setProjectID", this.projectId);
            $(this.$refs.nameNewTag).val("");
        }
    }
}
</script>

<style scoped>
</style>
