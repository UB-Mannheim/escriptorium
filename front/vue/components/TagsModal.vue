<template>
    <div class="modal fade" id="tagsModal" ref="tagsModal" tabindex="-1" role="dialog" aria-labelledby="tagsModalLabel" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered modal-md" id="modaltag" role="document">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Assign tags</h5>
                    <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                        <span aria-hidden="true">&times;</span>
                    </button>
                </div>
                <form method="post" action="#" id="formTag" ref="formTag">
                    <div class="modal-body">
                        <input type="hidden" class="form-control" id="project-id" name="project" v-model="projectIdComputed">
                        <input type="hidden" class="form-control" id="document-id" name="document" v-model="documentId">
                        <input type="hidden" class="form-control" id="valuesSelected" name="selectedtags" v-model="valuesSelected">
                        <input type="hidden" class="form-control" id="checkboxlist" name="checkboxlist" v-model="checkboxListData">
                        <div class="form-row form-group justify-content-center">
                            <select name="tags" id="mselect-tags" ref="mselectTags" v-model="valuesSelected" data-live-search="true" data-live-search-placeholder="filters" multiple>
                                <option v-for="tag in tags" :key="tag.pk" v-bind:value="tag.pk" >
                                    {{ tag.name }}
                                </option>
                            </select>
                        </div>
                        <div class="form-row form-group justify-content-center">
                            <input type="text" class="form-control" name="name" placeholder="Add a new tag" style="width: 50%;">
                            <input type="color" class="form-control" name="color" style="width: 10%;">
                        </div>

                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>
                        <button type="button" class="btn btn-primary" v-on:click="updateTagList">Save</button>
                    </div>
                </form>
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
            valuesSelected: [],
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
            return this.projectId
        },
        checkboxListData() {
            return this.$store.state.documentslist.checkboxList;
        }
    },
    mounted(){
        $(this.$refs.tagsModal).on("show.bs.modal", this.populateItems);
        $(this.$refs.tagsModal).on("hide.bs.modal", this.hideModal);
    },
    updated: function(){
        this.$nextTick(function(){ 
            $(this.$refs.mselectTags).selectpicker({
                liveSearch: true,
                size: 'auto',
                width: 'auto'
            });
        });
    },
    methods: {
        async updateTagList(){
            let json_data = this.buildJSONData($(this.$refs.formTag)[0].elements);
            await this.$store.dispatch('documentslist/updateDocumentTags', json_data);
            $(this.$refs.tagsModal).modal('hide');
            document.location.reload();
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
            return element
        },
        hideModal(){
            this.$store.commit('documentslist/setDocumentID', null);
        },
        async populateItems(){
            this.$store.commit('documentslist/setProjectID', this.projectId);
            if(!this.documentId) await this.$store.dispatch('documentslist/getAllTagsProject');
        }

    },
    watch: {
        "$store.state.documentslist.mapTags": {
            handler: function(nv) {
                this.tags = nv;
                this.$nextTick(function(){ 
                    this.valuesSelected = this.listCheckedTags;
                    $(this.$refs.mselectTags).selectpicker('val', this.listCheckedTags); 
                    $(this.$refs.mselectTags).selectpicker('refresh'); 
                });
            },
            immediate: true 
        }
    }
}
</script>

<style scoped>
</style>



