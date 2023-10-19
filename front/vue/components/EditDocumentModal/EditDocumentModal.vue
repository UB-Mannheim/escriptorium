<template>
    <EscrModal class="escr-edit-document">
        <template #modal-header>
            <h2>{{ newDocument ? "Create New" : "Edit" }} Document</h2>
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
                placeholder="Name"
                :disabled="disabled"
                :max-length="512"
                :on-input="(e) => handleTextFieldInput('name', e.target.value)"
                :value="name"
                required
            />
            <DropdownField
                label="Script"
                :disabled="disabled"
                :on-change="handleMainScriptChange"
                :options="scriptOptions"
                required
            />
            <DropdownField
                label="Read Direction"
                :disabled="disabled"
                :help-text="(
                    'The read direction describes the overall order of elements/pages in the ' +
                    'document; NOT the order of words in a line, which will be automatically ' +
                    'determined by the script.'
                )"
                :on-change="(e) => handleTextFieldInput('readDirection', e.target.value)"
                :options="readDirectionOptions"
                required
            />
            <DropdownField
                label="Line Position"
                help-text="The position of the line relative to the polygon."
                :disabled="disabled"
                :on-change="(e) => handleTextFieldInput('linePosition', e.target.value)"
                :options="linePositionOptions"
                required
            />
            <MetadataField
                :disabled="disabled"
                :items="metadata"
                :on-change="handleUpdateMetadatum"
                :on-add="handleAddMetadatum"
                :on-remove="handleRemoveMetadatum"
            />
            <TagsField
                label="Tags"
                :disabled="disabled"
                :on-change="handleTagsFieldInput"
                :on-change-tag-name="(e) => handleTextFieldInput('tagName', e.target.value)"
                :on-create-tag="onCreateTag"
                :tag-name="tagName"
                :tags="tags"
                :selected-tags="selectedTags"
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
                :label="newDocument ? 'Create' : 'Save'"
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
import TagsField from "../TagsField/TagsField.vue";
import TextField from "../TextField/TextField.vue";
import XIcon from "../Icons/XIcon/XIcon.vue";
import "./EditDocumentModal.css";

export default {
    name: "EscrEditDocumentModal",
    components: {
        DropdownField,
        EscrButton,
        EscrModal,
        MetadataField,
        TextField,
        XIcon,
        TagsField
    },
    props: {
        /**
         * Boolean indicating if the form fields should be disabled
         */
        disabled: {
            type: Boolean,
            default: false,
        },
        /**
         * If this is a new document, set true; if it's editing an existing one, leave false
         */
        newDocument: {
            type: Boolean,
            default: false,
        },
        /**
         * Callback for clicking the cancel button
         */
        onCancel: {
            type: Function,
            required: true,
        },
        /**
         * Callback for clicking the "create tag" button
         */
        onCreateTag: {
            type: Function,
            required: true,
        },
        /**
         * Callback for clicking the save/create button
         */
        onSave: {
            type: Function,
            required: true,
        },
        /**
         * Full list of scripts from the database
         */
        scripts: {
            type: Array,
            required: true,
        },
        /**
         * Full list of tags across all documents
         */
        tags: {
            type: Array,
            default: () => [],
        },
    },
    computed: {
        ...mapState({
            linePosition: (state) => state.forms.editDocument.linePosition,
            mainScript: (state) => state.forms.editDocument.mainScript,
            metadata: (state) => state.forms.editDocument.metadata,
            name: (state) => state.forms.editDocument.name,
            readDirection: (state) => state.forms.editDocument.readDirection,
            selectedTags: (state) => state.forms.editDocument.tags,
            tagName: (state) => state.forms.editDocument.tagName,
        }),
        /**
         * Consider the form invalid if missing required fields.
         */
        invalid() {
            return !this.name ||
                !this.readDirection ||
                !this.mainScript ||
                (!this.linePosition && this.linePosition !== 0) ||
                this.metadata.some((meta) => !meta.key?.name || !meta.value);
        },
        /**
         * Populate dropdown options for line position.
         */
        linePositionOptions() {
            return ["Baseline", "Topline", "Centered"].map((linePos, idx) => ({
                value: idx.toString(),
                label: linePos,
                selected: idx.toString() === this.linePosition.toString(),
            }));
        },
        /**
         * Populate dropdown options for read direction.
         */
        readDirectionOptions() {
            return [
                {
                    value: "ltr",
                    label: "Left to right",
                    selected: this.readDirection === "ltr",
                },
                {
                    value: "rtl",
                    label: "Right to left",
                    selected: this.readDirection === "rtl",
                }
            ];
        },
        /**
         * Populate dropdown options for script.
         */
        scriptOptions() {
            return this.scripts.map((script) => ({
                value: script.name,
                label: script.name,
                selected: script.name === this.mainScript,
            }));
        },
    },
    methods: {
        ...mapActions("forms", [
            "handleGenericInput",
            "handleTagsInput",
            "handleMetadataInput",
        ]),
        handleAddMetadatum(index) {
            this.handleMetadataInput({
                form: "editDocument",
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
                form: "editDocument",
                action: "update",
                metadatum: updatedMetadatum,
            })
        },
        handleRemoveMetadatum(metadatum) {
            this.handleMetadataInput({
                form: "editDocument",
                action: "remove",
                metadatum,
            });
        },
        handleTagsFieldInput({ checked, tag }) {
            this.handleTagsInput({ checked, tag, form: "editDocument" });
        },
        handleTextFieldInput(field, value) {
            this.handleGenericInput({ field, value, form: "editDocument" });
        },
        handleMainScriptChange(e) {
            this.handleTextFieldInput("mainScript", e.target.value);
            const script = this.scripts.find(
                (script) => script.name === e.target.value
            );
            const readDirection = script.text_direction.endsWith("-rl") ? "rtl" : "ltr";
            this.handleTextFieldInput("readDirection", readDirection);
        }
    },
}
</script>
