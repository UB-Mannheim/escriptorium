<template>
    <EscrModal
        class="escr-transcribe-modal"
    >
        <template #modal-header>
            <h2>Transcribe {{ scope }}</h2>
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
            <EscrAlert
                color="secondary"
                message="Check accuracy of segmentation prior to transcribing."
            />
            <AutocompleteField
                label="Model"
                :disabled="disabled || !models"
                :option-groups="modelOptionGroups"
                :on-change="handleModelChange"
                required
            />
            <TextField
                :disabled="disabled"
                help-text="Enter a name for the new transcription layer."
                :max-length="512"
                :on-input="handleLayerNameInput"
                :value="layerName"
                placeholder="Enter layer name"
                label="Layer Name"
                required
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
                label="Transcribe"
                :on-click="onSubmit"
                :disabled="disabled || invalid"
            />
        </template>
    </EscrModal>
</template>
<script>
import { mapActions, mapState } from "vuex";
import AutocompleteField from "../AutocompleteDropdown/AutocompleteField.vue";
import DropdownField from "../Dropdown/DropdownField.vue";
import EscrAlert from "../Alert/Alert.vue";
import EscrButton from "../Button/Button.vue";
import EscrModal from "../Modal/Modal.vue";
import TextField from "../TextField/TextField.vue";
import XIcon from "../Icons/XIcon/XIcon.vue";
import "../Common/Form.css";

export default {
    name: "EscrTranscribeModal",
    components: {
        AutocompleteField,
        DropdownField,
        EscrAlert,
        EscrButton,
        EscrModal,
        TextField,
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
         * Scope of the transcription task, which will appear in the header to indicate
         * whether you are transcribing the entire document or specific images.
         */
        scope: {
            type: String,
            required: true,
        },
        /**
         * Callback function for submitting the transcription task.
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
            model: (state) => state.forms.transcribe.model,
            layerName: (state) => state.forms.transcribe.layerName,
        }),
        /**
         * this form is invalid and cannot be submitted if it is missing model
         * or layer name
         */
        invalid() {
            return !this.layerName || !this.model;
        },
        /**
         * Group models into "Your Models", "Shared Models", and "Public Models"
         */
        modelOptionGroups() {
            const yourModels = [];
            const sharedModels = [];
            const publicModels = [];

            this.models.forEach((model) => {
                const option = {
                    label: model.name,
                    value: model.pk.toString(),
                    selected: this.model.toString() === model.pk.toString(),
                };

                if (model.rights === "owner") {
                    yourModels.push(option);
                } else if (model.rights === "public") {
                    publicModels.push(option);
                } else {
                    // model.rights === "user" (shared)
                    sharedModels.push(option);
                }
            });

            const groups = [];
            if (yourModels.length > 0) {
                groups.push({ label: "Your Models", options: yourModels });
            }
            if (sharedModels.length > 0) {
                groups.push({ label: "Shared Models", options: sharedModels });
            }
            if (publicModels.length > 0) {
                groups.push({ label: "Public Models", options: publicModels });
            }

            return groups;
        },
    },
    methods: {
        ...mapActions("forms", [
            "handleGenericInput",
        ]),
        handleLayerNameInput(e) {
            this.handleGenericInput({
                form: "transcribe", field: "layerName", value: e.target.value,
            });
        },
        handleModelChange(e) {
            this.handleGenericInput({ form: "transcribe", field: "model", value: e.target.value });
        },
    },
};
</script>
