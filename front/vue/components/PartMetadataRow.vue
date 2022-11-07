<template>
    <div class="input-group input-group-sm mb-2">
        <div class="input-group-sm input-group-prepend">
            <input type="text"
                   class="form-control input-group-text"
                   :id="'id_metadata_set_key-' + rowId"
                   title="Key"
                   autocomplete="on"
                   placeholder="Key"
                   @focusin="editInput(true)"
                   @focusout="updateKey"
                   :value="rowName">
        </div>

        <input type="text"
               class="form-control"
               :id="'id_metadata_set_value-' + rowId"
               title="Value"
               maxlength="512"
               placeholder="Value"
               @focusin="editInput(true)"
               @focusout="updateValue"
               :value="rowValue">

        <div class="input-group-sm input-group-prepend">
            <button class="btn btn-success"
                    v-if="metadata==null"
                    id="id_metadata_add"
                    @click="addMetadata($event)"
                    type="button">+</button>

            <button class="btn btn-danger"
                    v-if="metadata!=null"
                    :id="'id_metadata_del-' + rowId"
                    @click="deleteMetadata($event)"
                    type="button">✗</button>
        </div>
    </div>
</template>

<script>
 export default Vue.extend({
     props: ['metadata'],
     computed: {
         rowId() {
             return this.metadata != null ? this.metadata.pk : null;
         },
         rowName() {
             return this.metadata != null ? this.metadata.key.name : null;
         },
         rowValue() {
             return this.metadata != null ? this.metadata.value : null;
         }
     },
     methods: {
         editInput(focus) {
             this.$store.commit('document/setBlockShortcuts', focus);
         },

         async addMetadata() {
             var keyInput = document.getElementById('id_metadata_set_key-null');
             var valInput = document.getElementById('id_metadata_set_value-null')
             await this.$store.dispatch('parts/createPartMetadata', {
                 "key": {"name": keyInput.value},
                 "value": valInput.value
             });
             keyInput.value = '';
             valInput.value = '';
         },

         async deleteMetadata(ev) {
             await this.$store.dispatch('parts/deletePartMetadata', this.metadata.pk);
         },

         async updateKey(ev) {
             this.editInput(false);
             if (this.metadata == null) return;
             if (ev.target.value != this.metadata.key.name) {
                 await this.$store.dispatch('parts/updatePartMetadata', {
                     pk: this.metadata.pk,
                     data: {
                         key: {name: ev.target.value}
                     }
                 });
             }
         },

         async updateValue(ev) {
             this.editInput(false);
             if (this.metadata == null) return;
             if (ev.target.value != this.metadata.value) {
                 await this.$store.dispatch('parts/updatePartMetadata', {
                     pk: this.metadata.pk,
                     data: {
                         value: ev.target.value
                     }
                 });
             }
         }
     }
 })
</script>
