<template>
    <div class="col panel">
        <div class="tools">
            <i title="Visual Transcription Panel"
               class="panel-icon fas fa-language"></i>
        </div>
        <div class="content-container" ref="formContainer">
            <div ref="contentform" class="content-container">
                <div class="form-group col-xl">
                    <label for="partName">Name</label>
                    <input type="text"
                           class="form-control"
                           :placeholder="partTitle"
                           id="partName"
                           ref="partName"
                           v-model="partName"
                           @focusin="editInput(true)"
                           @focusout="editInput(false)">
                    <small class="form-text text-muted">If left empty the name will automatically be {typology+index number}</small>
                </div>
                <div class="form-group col-xl">
                    <label for="partTypology">Typology</label>
                    <select class="form-control input-group-prepend w-100"
                            id="partTypology"
                            v-model="typology">
                      <option v-for="t in typologies"
                              :key="t.pk"
                              :value="t.pk"
                              :selected="t.pk == typology">{{t.name}}</option>
                    </select>
                </div>

                <div class="form-group col-xl">
                    <label for="partComments">Comments</label>
                    <textarea id="partComments"
                              @focusin="editInput(true)"
                              @focusout="editInput(false)"
                              @keyup="adjustHeight"
                              name="partComments"
                              class="form-control"
                              v-model.lazy="comments">
                    </textarea>
                </div>

                <div class="form-group col-xl">
                    <label>Metadata</label>
                    <div id="metadata-form" class="js-metadata-form">

                        <partmetadatarow v-for="metadata in metadatas"
                                         :key="metadata.id"
                                         :metadata="metadata"></partmetadatarow>
                        <emptypartmetadatarow :metadata="null"></emptypartmetadatarow>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
 import PartMetadataRow from './PartMetadataRow.vue';

 export default {
     components: {
         'partmetadatarow': PartMetadataRow,
         'emptypartmetadatarow': PartMetadataRow,
     },

     computed: {
         partName: {
             get: function () {
                 return this.$store.state.parts.name;
             },
             set: async function (newValue) {
                 await this.$store.dispatch('parts/updatePart', {"name": newValue});
             }
         },

         partTitle() {
             return this.$store.state.parts.title;
         },

         comments: {
             get: function () {
                 return this.$store.state.parts.comments;
             },
             set: async function(value) {
                 await this.$store.dispatch('parts/updatePart', {"comments": value});
             }
         },

         typology: {
             get: function() {
                 return this.$store.state.parts.typology;
             },
             set: async function(value) {
                 await this.$store.dispatch('parts/updatePart', {"typology": value});
             }
         },

         typologies() {
             return this.$store.state.document.types.parts;
         },

         metadatas() {
             return this.$store.state.parts.metadata;
         }
     },
     mounted(){
         this.adjustHeight({target: document.getElementById('partComments')});
     },
     methods: {
         editInput(bool) {
             this.$store.commit('document/setBlockShortcuts', bool);
         },

         adjustHeight(el) {
             el.target.style.height = (el.target.scrollHeight > el.target.clientHeight) ? (el.target.scrollHeight)+"px" : "60px";
         },
     },
 }
</script>

<style scoped>
</style>
