<template>
    <div class="input-group input-group-sm mb-2">
        <div class="input-group-sm input-group-prepend">
            <input
                :id="'id_metadata_set_key-' + rowId"
                type="text"
                class="form-control input-group-text"
                title="Key"
                autocomplete="on"
                placeholder="Key"
                :value="rowName"
                @focusin="editInput(true)"
                @focusout="updateKey"
            >
        </div>

        <input
            :id="'id_metadata_set_value-' + rowId"
            type="text"
            class="form-control"
            title="Value"
            maxlength="512"
            placeholder="Value"
            :value="rowValue"
            @focusin="editInput(true)"
            @focusout="updateValue"
        >

        <div class="input-group-sm input-group-prepend">
            <button
                v-if="metadata==null"
                id="id_metadata_add"
                class="btn btn-success"
                type="button"
                @click="addMetadata($event)"
            >
                +
            </button>

            <button
                v-if="metadata!=null"
                :id="'id_metadata_del-' + rowId"
                class="btn btn-danger"
                type="button"
                @click="deleteMetadata($event)"
            >
                ✗
            </button>
        </div>
    </div>
</template>

<script>
export default Vue.extend({
    props: ["metadata"],
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
            this.$store.commit("document/setBlockShortcuts", focus);
        },

        async addMetadata() {
            var keyInput = document.getElementById("id_metadata_set_key-null");
            var valInput = document.getElementById("id_metadata_set_value-null")
            await this.$store.dispatch("parts/createPartMetadata", {
                "key": {"name": keyInput.value},
                "value": valInput.value
            });
            keyInput.value = "";
            valInput.value = "";
        },

        async deleteMetadata(ev) {
            await this.$store.dispatch("parts/deletePartMetadata", this.metadata.pk);
        },

        async updateKey(ev) {
            this.editInput(false);
            if (this.metadata == null) return;
            if (ev.target.value != this.metadata.key.name) {
                await this.$store.dispatch("parts/updatePartMetadata", {
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
                await this.$store.dispatch("parts/updatePartMetadata", {
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
