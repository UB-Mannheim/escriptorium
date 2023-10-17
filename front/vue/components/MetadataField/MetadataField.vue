<template>
    <fieldset class="escr-form-field escr-metadata-field">
        <legend class="escr-field-label">
            Metadata
        </legend>
        <div
            v-for="item in items"
            :key="item.pk || item.index"
            class="metadatum"
        >
            <input
                type="text"
                :disabled="disabled"
                :value="item.key && item.key.name"
                placeholder="Key"
                @input="(e) => onChange(item, 'key', e.target.value)"
            >
            <input
                type="text"
                :disabled="disabled"
                :value="item.value"
                placeholder="Value"
                @input="(e) => onChange(item, 'value', e.target.value)"
            >
            <EscrButton
                :disabled="disabled"
                :on-click="() => onRemove(item)"
                color="outline-danger"
                size="small"
            >
                <template #button-icon>
                    <XIcon />
                </template>
            </EscrButton>
        </div>
        <EscrButton
            :disabled="disabled"
            :on-click="handleAddMetadatum"
            label="Add New"
            size="small"
        >
            <template #button-icon>
                <PlusIcon />
            </template>
        </EscrButton>
    </fieldset>
</template>
<script>
import EscrButton from "../Button/Button.vue";
import PlusIcon from "../Icons/PlusIcon/PlusIcon.vue";
import XIcon from "../Icons/XIcon/XIcon.vue";
import "./MetadataField.css";

export default {
    name: "EscrMetadataField",
    components: { EscrButton, PlusIcon, XIcon },
    props: {
        /**
         * Whether or not this field is disabled
         */
        disabled: {
            type: Boolean,
            default: false,
        },
        /**
         * Callback function for adding a new metadatum
         */
        onAdd: {
            type: Function,
            required: true,
        },
        /**
         * Callback function for changing the metadata set
         */
        onChange: {
            type: Function,
            required: true,
        },
        /**
         * Callback function for removing a metadatum
         */
        onRemove: {
            type: Function,
            required: true,
        },
        /**
         * The current form state for metadata, an array of items each structured like:
         * {
         *     pk?: Number,
         *     key: {
         *         name: String
         *     },
         *     value: String,
         * }
         */
        items: {
            type: Array,
            required: true,
        },
    },
    data() {
        return {
            newMetaIndex: 1,
        }
    },
    methods: {
        /**
         * Handle clicking the "add new" button
         */
        handleAddMetadatum() {
            // call the callback with the current index
            this.onAdd(this.newMetaIndex);
            // increment index of added metadata so that we can properly track them individually
            this.newMetaIndex += 1;
        },
    },
}
</script>
