<template>
    <EscrModal
        class="escr-segment-modal"
    >
        <template #modal-header>
            <h2>Segment {{ scope }}</h2>
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
            <DropdownField
                label="Model"
                :disabled="disabled || !models"
                :options="modelOptions"
                :on-change="handleModelChange"
                required
            />
            <ArrayField
                :on-change="handleIncludeChange"
                :options="includeOptions"
                label="Include"
                required
            />
            <DropdownField
                label="Text Direction"
                :disabled="disabled"
                :options="textDirectionOptions"
                :on-change="handleTextDirectionChange"
                required
            />
            <div class="escr-form-field escr-checkbox-field escr-overwrite-field">
                <label>
                    <input
                        type="checkbox"
                        value="overwrite"
                        :checked="overwrite === true"
                        @change="handleOverwriteChange"
                    >
                    Overwrite Existing Segmentation and Transcriptions
                </label>
                <span class="escr-help-text">
                    If checked, all existing segmentation and bound transcriptions will be deleted.
                </span>
            </div>
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
                label="Segment"
                :on-click="onSubmit"
                :disabled="disabled || invalid"
            />
        </template>
    </EscrModal>
</template>
<script>
import { mapActions, mapState } from "vuex";
import EscrButton from "../Button/Button.vue";
import EscrModal from "../Modal/Modal.vue";
import XIcon from "../Icons/XIcon/XIcon.vue";
import DropdownField from "../Dropdown/DropdownField.vue";
import "../Common/Form.css";
import "./SegmentModal.css";
import ArrayField from "../ArrayField/ArrayField.vue";

export default {
    name: "EscrSegmentModal",
    components: {
        ArrayField,
        DropdownField,
        EscrButton,
        EscrModal,
        XIcon,
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
         * The list of all OCR models on the document. Should be an array of objects
         * with at least a name and pk for each model.
         */
        models: {
            type: Array,
            required: true,
        },
        /**
         * Scope of the segmentation task, which will appear in the header to indicate
         * whether you are segmenting the entire document or specific images.
         */
        scope: {
            type: String,
            required: true,
        },
        /**
         * Callback function for submitting the segmentation task.
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
    },
    computed: {
        ...mapState({
            include: (state) => state.forms.segment.include,
            model: (state) => state.forms.segment.model,
            overwrite: (state) => state.forms.segment.overwrite,
            textDirection: (state) => state.forms.segment.textDirection,
        }),
        /**
         * this form is invalid and cannot be submitted if it is missing model,
         * text direction, or segmentation steps to include
         */
        invalid() {
            return !this.textDirection || this.include.length === 0;
        },
        /**
         * convert include to options for checkbox elements
         */
        includeOptions() {
            return [
                {
                    label: "Lines",
                    value: "lines",
                    selected: this.include.includes("lines"),
                },
                {
                    label: "Regions",
                    value: "regions",
                    selected: this.include.includes("regions"),
                },
            ];
        },
        /**
         * convert models to options for select element
         */
        modelOptions() {
            const defaultModel = [{
                label: "Default Segmentation Model",
                value: null,
                selected: !this.model,
            }];
            const otherModels = this.models.map((model) => ({
                label: model.name,
                value: model.pk,
                selected: this.model.toString() === model.pk.toString(),
            }));
            return defaultModel.concat(otherModels);
        },
        /**
         * collect text direction options for select element
         */
        textDirectionOptions() {
            return [
                {
                    label: "Horizontal Left to Right",
                    value: "horizontal-lr",
                    selected: this.textDirection === "horizontal-lr",
                },
                {
                    label: "Horizontal Right to Left",
                    value: "horizontal-rl",
                    selected: this.textDirection === "horizontal-rl",
                },
                {
                    label: "Vertical Left to Right",
                    value: "vertical-lr",
                    selected: this.textDirection === "vertical-lr",
                },
                {
                    label: "Vertical Right to Left",
                    value: "vertical-rl",
                    selected: this.textDirection === "vertical-rl",
                },
            ];
        },
    },
    methods: {
        ...mapActions("forms", [
            "handleCheckboxArrayInput",
            "handleGenericInput",
        ]),
        handleIncludeChange(e) {
            this.handleCheckboxArrayInput({
                form: "segment", field: "include", checked: e.target.checked, value: e.target.value,
            });
        },
        handleModelChange(e) {
            this.handleGenericInput({ form: "segment", field: "model", value: e.target.value });
        },
        handleOverwriteChange(e) {
            this.handleGenericInput({
                form: "segment", field: "overwrite", value: e.target.checked
            });
        },
        handleTextDirectionChange(e) {
            this.handleGenericInput({
                form: "segment", field: "textDirection", value: e.target.value,
            });
        },
    },
};
</script>
