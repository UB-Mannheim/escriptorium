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
        <form method="post" action="#" id="formrmtag">
            <div class="modal-body">
            <input type="hidden" class="form-control" id="project-id" name="project" v-model="project_id">
            <input type="hidden" class="form-control" id="document-id" name="document" v-model="document_id">
            <input type="hidden" class="form-control" id="valuesselected" name="selctedtags" v-model="valuesselected">
            <input type="hidden" class="form-control" id="checkboxlist" name="checkboxlist" v-model="checkboxlist_data">
            <div class="form-row form-group justify-content-center">
                <select name="tags" v-bind:id="'mselect-tags'" v-model="valuesselected" data-live-search="true" multiple>
                    <option v-for="tag in tags" :key="tag.pk" v-bind:value="tag.pk" >
                        {{ tag.name }}
                    </option>
                </select>
            </div>

            </div>
            <div><h5 id="errortag">{{ form_field_errors}}</h5></div>
            <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>
            <button type="button" class="btn btn-primary" v-on:click="updatetaglist">Save</button>
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
            valuesselected: [],
            tags: []
        }
    },
    computed: {
        document_id() {
            return this.$store.state.documentslist.documentID;
        },
        form_field_errors() {
            return this.$store.state.documentslist.form_field_errors;
        },
        list_checked_tags() {
            return this.$store.state.documentslist.checkedtags;
        },
        project_id() {
            return this.$store.state.documentslist.projectID;
        },
        checkboxlist_data() {
            return this.$store.state.documentslist.checkboxlist;
        }
    },
    mounted(){
        $(this.$refs.tagsModal).on("show.bs.modal", this.populateItems);
        $(this.$refs.tagsModal).on("hide.bs.modal", this.hideModal);
    },
    updated: function(){
        this.$nextTick(function(){ 
            $('#mselect-tags').selectpicker({
                liveSearch: true,
                size: 'auto',
                width: 'auto'
            });
        });
    },
    methods: {
        async updatetaglist(){
            let json_data = this.buildjsondata(document.getElementById("formrmtag").elements);
            await this.$store.dispatch('documentslist/updatedocumenttags', json_data);
            $("#tagsModal").modal('hide');
            document.location.reload();
        },
        buildjsondata(el){
            let element = {};
            let tabindex = [];
            for(let i = 0; i < el.length; i++){
                if((el[i].value.toLowerCase() != "button") && (el[i].value.toLowerCase() != "submit") /*&& (el[i].value != "")*/){
                    if(!tabindex.includes(el[i].name.toString())){
                        Object.defineProperty(element, el[i].name, { value: el[i].value });
                    }
                    tabindex.push(el[i].name.toString());
                }
            }
            return JSON.stringify(element, tabindex);
        },
        isChecked(id){
            return this.list_checked_tags.includes(id)
        },
        hideModal(){
            this.$store.commit('documentslist/setDocumentID', 0);
            this.$store.commit('documentslist/setProjectID', 0);
        },
        async populateItems(){
            this.$store.commit('documentslist/setProjectID', $(this.$refs.tagsModal).attr('project_id'));
            if(this.document_id == 0) await this.$store.dispatch('documentslist/getalltagsproject');
        }
    },
    watch: {
        "$store.state.documentslist.maptags": {
            handler: function(nv) {
                this.tags = nv;
                this.$nextTick(function(){ 
                    $('#mselect-tags').selectpicker('val', this.list_checked_tags); 
                    $('#mselect-tags').selectpicker('refresh'); 
                });
            },
            immediate: true 
        }
    }
}
</script>

<style scoped>
</style>



