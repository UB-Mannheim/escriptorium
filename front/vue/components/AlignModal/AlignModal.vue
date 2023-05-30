<template>
    <EscrModal class="escr-align-modal">
        <template #modal-header>
            <h2>Align {{ scope }}</h2>
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
            <h3>
                Transcription<span
                    aria-label="required"
                    class="escr-required"
                >*</span>
            </h3>
            <DropdownField
                label="Transcription"
                :disabled="disabled || !transcriptions"
                :options="transcriptionOptions"
                :on-change="handleTranscriptionChange"
                :label-visible="false"
                required
            />
            <hr>
            <h3>
                Textual Witness<span
                    aria-label="required"
                    class="escr-required"
                >*</span>
            </h3>
            <div class="escr-form-field">
                <SegmentedButtonGroup
                    color="secondary"
                    name="align-textual-witness-type"
                    :disabled="disabled"
                    :options="textalWitnessTypeOptions"
                    :on-change-selection="handleTextualWitnessTypeChange"
                />
                <DropdownField
                    v-if="textualWitnessType === 'select'"
                    label="Textual witness"
                    :disabled="disabled || !textualWitnesses"
                    :options="textualWitnessOptions"
                    :on-change="handleTextualWitnessSelectionChange"
                    :label-visible="false"
                    required
                />
                <input
                    v-else
                    type="file"
                    @change="handleFileChange"
                >
            </div>
            <hr>
            <h3 class="escr-align-settings">
                Settings <EscrButton
                    color="link-secondary"
                    :label="`${showAdvanced ? 'Hide' : 'Show'} advanced settings`"
                    :on-click="showHideAdvanced"
                />
            </h3>
            <TextField
                :disabled="disabled"
                help-text="Name for the new transcription layer produced by this alignment."
                :on-input="handleLayerNameInput"
                :value="layerName"
                :max-length="512"
                placeholder="Enter layer name"
                label="Layer Name"
                required
            />
            <EscrAlert
                v-if="overwriteWarningVisible"
                color="danger"
                message="Reusing an existing layer name will overwrite that layer."
            />
            <ArrayField
                :on-change="handleRegionTypesChange"
                :options="regionTypesOptions"
                class="escr-region-types"
                help-text="Select region types to include in the alignment."
                label="Region Types"
            />
            <div class="escr-form-field escr-fulldoc-field escr-checkbox-field">
                <label>
                    <input
                        type="checkbox"
                        value="use-full"
                        :checked="fullDoc === true"
                        @change="handleUseFullChange"
                    >
                    Use full transcribed document
                </label>
                <span class="escr-help-text">
                    If checked, the aligner will use all transcribed pages of the document to find
                    matches. If unchecked, it will compare each page to the text separately.
                </span>
            </div>
            <div class="escr-form-field escr-merge-field escr-checkbox-field">
                <label>
                    <input
                        type="checkbox"
                        value="merge"
                        :checked="merge === true"
                        @change="handleMergeChange"
                    >
                    Merge aligned text with existing transcription
                </label>
                <span class="escr-help-text">
                    If checked, the aligner will reuse the text of the original transcription when
                    alignment could not be performed; if unchecked, those lines will be blank.
                </span>
            </div>
            <hr v-if="showAdvanced">
            <AlignAdvancedFieldset
                v-if="showAdvanced"
                :disabled="disabled"
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
                label="Align"
                :on-click="onSubmit"
                :disabled="disabled || invalid"
            />
        </template>
    </EscrModal>
</template>
<script>
import { mapActions, mapState } from "vuex";
import AlignAdvancedFieldset from "./AlignAdvancedFieldset.vue";
import ArrayField from "../ArrayField/ArrayField.vue";
import DropdownField from "../Dropdown/DropdownField.vue";
import EscrAlert from "../Alert/Alert.vue";
import EscrButton from "../Button/Button.vue";
import EscrModal from "../Modal/Modal.vue";
import SegmentedButtonGroup from "../SegmentedButtonGroup/SegmentedButtonGroup.vue";
import TextField from "../TextField/TextField.vue";
import XIcon from "../Icons/XIcon/XIcon.vue";
import "../Common/Form.css";
import "./AlignModal.css";

export default {
    name: "EscrAlignModal",
    components: {
        AlignAdvancedFieldset,
        ArrayField,
        DropdownField,
        EscrAlert,
        EscrButton,
        EscrModal,
        TextField,
        XIcon,
        SegmentedButtonGroup,
    },
    props: {
        /**
         * Boolean indicating whether or not the form fields should be disabled.
         */
        disabled: {
            type: Boolean,
            required: true,
        },
        /**
         * List of all region types on this document.
         */
        regionTypes: {
            type: Array,
            required: true,
        },
        /**
         * List of all transcription layers on this document.
         */
        transcriptions: {
            type: Array,
            required: true,
        },
        /**
         * Scope of the alignment task, which will appear in the header to indicate
         * whether you are aligning the entire document or specific images.
         */
        scope: {
            type: String,
            required: true,
        },
        /**
         * Callback function for submitting the alignment task.
         */
        onSubmit: {
            type: Function,
            required: true,
        },
        /**
         * Callback function for clicking "cancel".
         */
        onCancel: {
            type: Function,
            required: true,
        },
        /**
         * List of textual witnesses to preselect from, which should each be an object including
         * a name and pk.
         */
        textualWitnesses: {
            type: Array,
            required: true,
        },
    },
    computed: {
        ...mapState({
            layerName: (state) => state.forms.align.layerName,
            formRegionTypes: (state) => state.forms.align.regionTypes,
            formTextualWitness: (state) => state.forms.align.textualWitness,
            overwriteWarningVisible: (state) => state.forms.align.overwriteWarningVisible,
            showAdvanced: (state) => state.forms.align.showAdvanced,
            transcriptionLayer: (state) => state.forms.align.transcription,
            textualWitnessFile: (state) => state.forms.align.textualWitnessFile,
            textualWitnessType: (state) => state.forms.align.textualWitnessType,
            fullDoc: (state) => state.forms.align.fullDoc,
            merge: (state) => state.forms.align.merge,
        }),
        /**
         * this form is invalid and cannot be submitted if it is missing model
         * or layer name, or the textual witness has not been selected/uploaded
         */
        invalid() {
            return !this.layerName ||
            !this.transcriptionLayer ||
            (this.textualWitnessType === "select" && !this.formTextualWitness) ||
            (this.textualWitnessType === "upload" && !this.textualWitnessFile);
        },
        /**
         * collect region types options for checkbox elements
         */
        regionTypesOptions() {
            return this.regionTypes.map((type) => ({
                label: type.name,
                value: type.pk.toString(),
                selected: this.formRegionTypes.includes(type.pk.toString()),
            }));
        },
        /**
         * Convert textual witness list to options for select element
         */
        textualWitnessOptions() {
            return this.textualWitnesses?.map((witness) => ({
                label: witness.name,
                value: witness.pk.toString(),
                selected: this.formTextualWitness.toString() === witness.pk.toString(),
            }));
        },
        /**
         * Switcher between selecting existing and uploading textual witness
         */
        textalWitnessTypeOptions() {
            return [
                {
                    label: "Select Existing",
                    value: "select",
                    selected: this.textualWitnessType === "select",
                },
                {
                    label: "Upload New",
                    value: "upload",
                    selected: this.textualWitnessType === "upload",
                },
            ]
        },
        /**
         * Convert transcription layers to options for select element
         */
        transcriptionOptions() {
            return this.transcriptions.map((transcription) => ({
                label: transcription.name,
                value: transcription.pk.toString(),
                selected: this.transcriptionLayer.toString() === transcription.pk.toString(),
            }));
        },
    },
    methods: {
        ...mapActions("forms", [
            "handleGenericInput",
            "handleCheckboxArrayInput",
        ]),
        handleFileChange(e) {
            this.handleGenericInput({
                form: "align",
                field: "textualWitnessFile",
                value: e.target.files[0],
            });
        },
        handleUseFullChange(e) {
            this.handleGenericInput({
                form: "align",
                field: "fullDoc",
                value: e.target.checked,
            });
        },
        handleMergeChange(e) {
            this.handleGenericInput({
                form: "align",
                field: "merge",
                value: e.target.checked,
            });
        },
        handleLayerNameInput(e) {
            this.handleGenericInput({
                form: "align", field: "layerName", value: e.target.value,
            });
            // turn on the overwrite warning if the user enters an existing layer name
            if (
                !this.overwriteWarningVisible &&
                this.transcriptions.some((t) => t.name === e.target.value)
            ) {
                this.handleGenericInput({
                    form: "align",
                    field: "overwriteWarningVisible",
                    value: true,
                });
            } else if (this.overwriteWarningVisible) {
                this.handleGenericInput({
                    form: "align",
                    field: "overwriteWarningVisible",
                    value: false,
                });
            }
        },
        handleTranscriptionChange(e) {
            this.handleGenericInput({
                form: "align",
                field: "transcription",
                value: e.target.value,
            });
        },
        handleTextualWitnessSelectionChange(e) {
            this.handleGenericInput({
                form: "align",
                field: "textualWitness",
                value: e.target.value,
            });
        },
        handleTextualWitnessTypeChange(value) {
            this.handleGenericInput({
                form: "align",
                field: "textualWitnessType",
                value,
            });
        },
        handleRegionTypesChange(e) {
            this.handleCheckboxArrayInput({
                form: "align",
                field: "regionTypes",
                checked: e.target.checked,
                value: e.target.value,
            });
        },
        showHideAdvanced() {
            this.handleGenericInput({
                form: "align",
                field: "showAdvanced",
                value: !this.showAdvanced,
            });
        },
    },
}
</script>
