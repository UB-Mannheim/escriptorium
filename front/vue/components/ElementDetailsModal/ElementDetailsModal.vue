<template>
    <EscrModal class="escr-element-details">
        <template #modal-header>
            <h2>Element Details</h2>
            <EscrButton
                color="text"
                :on-click="onCancel"
                size="small"
            >
                <template #button-icon>
                    <XIcon />
                </template>
            </EscrButton>
        </template>
        <template #modal-content>
            <TextField
                label="Name"
                :placeholder="partTitle"
                :disabled="disabled"
                :max-length="512"
                :on-input="(e) => handleTextFieldInput('name', e.target.value)"
                :value="name"
            />
            <DropdownField
                label="Typology"
                :disabled="disabled"
                :on-change="(e) => handleTextFieldInput(
                    'typology', e.target.value ? parseInt(e.target.value) : null
                )"
                :options="typologyOptions"
            />
            <dl class="escr-form-field">
                <dt class="escr-field-label">
                    Size
                </dt>
                <dd>
                    {{ size | prettyBytes }}
                </dd>
                <dt class="escr-field-label">
                    Dimensions
                </dt>
                <dd>
                    {{ image.size[0] }} x {{ image.size[1] }}
                </dd>
            </dl>
            <TextField
                label="Comments"
                :disabled="disabled"
                :on-input="(e) => handleTextFieldInput('comments', e.target.value)"
                :value="comments"
                textarea
            />
            <MetadataField
                :disabled="disabled"
                :items="metadata"
                :on-change="handleUpdateMetadatum"
                :on-add="handleAddMetadatum"
                :on-remove="handleRemoveMetadatum"
            />
        </template>
        <template #modal-actions>
            <EscrButton
                color="outline-primary"
                label="Cancel"
                :on-click="onCancel"
                :disabled="disabled"
            />
            <EscrButton
                color="primary"
                label="Save"
                :on-click="onSave"
                :disabled="disabled || invalid"
            />
        </template>
    </EscrModal>
</template>
<script>
import { mapActions, mapState } from "vuex";
import DropdownField from "../Dropdown/DropdownField.vue";
import EscrButton from "../Button/Button.vue";
import EscrModal from "../Modal/Modal.vue";
import MetadataField from "../MetadataField/MetadataField.vue";
import TextField from "../TextField/TextField.vue";
import XIcon from "../Icons/XIcon/XIcon.vue";
import "./ElementDetailsModal.css";

export default {
    name: "EscrElementDetailsModal",
    components: {
        DropdownField,
        EscrButton,
        EscrModal,
        MetadataField,
        XIcon,
        TextField,
    },
    props: {
        /**
         * If true, all buttons and form fields are disabled
         */
        disabled: {
            type: Boolean,
            required: true,
        },
        /**
         * Callback for canceling changes (by closing modal or clicking the cancel button)
         */
        onCancel: {
            type: Function,
            required: true,
        },
        /**
         * Callback for clicking the save button
         */
        onSave: {
            type: Function,
            required: true,
        },
    },
    computed: {
        ...mapState({
            comments: (state) => state.forms.elementDetails.comments,
            image: (state) => state.parts.image,
            metadata: (state) => state.forms.elementDetails.metadata,
            name: (state) => state.forms.elementDetails.name,
            partTitle: (state) => state.parts.title,
            size: (state) => state.parts.image_file_size,
            typology: (state) => state.forms.elementDetails.typology,
            validPartTypes: (state) => state.document.types.parts,
        }),
        /**
         * Consider the form invalid if missing required fields.
         */
        invalid() {
            return false;
        },
        typologyOptions() {
            return this.validPartTypes.map((type) => ({
                value: type.pk ? parseInt(type.pk) : null,
                label: type.name,
                selected: (type.pk ? parseInt(type.pk) : null) === this.typology,
            }));
        },
    },
    methods: {
        ...mapActions("forms", ["handleGenericInput", "handleMetadataInput"]),
        handleTextFieldInput(field, value) {
            this.handleGenericInput({ form: "elementDetails", field, value });
        },
        handleAddMetadatum(index) {
            this.handleMetadataInput({
                form: "elementDetails",
                action: "add",
                metadatum: {
                    key: {
                        name: "",
                    },
                    value: "",
                    index: `newMeta${index}`,
                }
            });
        },
        handleUpdateMetadatum(metadatum, field, value) {
            const updatedMetadatum = structuredClone(metadatum);
            switch (field) {
                case "key":
                    updatedMetadatum["key"]["name"] = value;
                    break;
                case "value":
                    updatedMetadatum["value"] = value;
                    break;
            }
            this.handleMetadataInput({
                form: "elementDetails",
                action: "update",
                metadatum: updatedMetadatum,
            })
        },
        handleRemoveMetadatum(metadatum) {
            this.handleMetadataInput({
                form: "elementDetails",
                action: "remove",
                metadatum,
            });
        },
    }
}
</script>
