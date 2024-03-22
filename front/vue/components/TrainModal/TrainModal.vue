<template>
    <EscrModal class="escr-train-modal">
        <template #modal-header>
            <h2>Train {{ scope }} Model</h2>
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
            <span class="escr-help-text">
                <p>
                    The training data will be generated from the selected images<span
                        v-if="
                            modalOpen.trainRecognizer
                        "
                    >
                        and trasncription. Empty lines will be ignored.
                    </span><span v-else>.</span>
                </p>
                <p>
                    Gathering data can take time and the model won't be available in the models tab
                    until then.
                </p>
            </span>
            <DropdownField
                v-if="modalOpen.trainRecognizer"
                label="Transcription"
                :disabled="disabled"
                :on-change="(e) => handleTextFieldInput('transcription', e.target.value)"
                :options="transcriptionOptions"
                :errors="dirty ? errors.transcription : []"
                required
            />
            <TextField
                label="New Model"
                placeholder="Name"
                :disabled="disabled"
                :max-length="512"
                :on-input="(e) => {
                    handleTextFieldInput('model', '');
                    handleTextFieldInput('modelName', e.target.value);
                }"
                :value="modelName"
                :invalid="!!modelName && !!model"
                :errors="dirty ? errors.modelName : []"
            />
            <DropdownField
                label="Or Select Existing"
                :disabled="disabled || !!modelName"
                :on-change="(e) => handleTextFieldInput('model', e.target.value)"
                :options="modelOptions"
                :errors="dirty ? errors.model : []"
            />
            <label class="escr-form-field">
                <input
                    type="checkbox"
                    value="override"
                    :checked="override === true"
                    @change="(e) => handleTextFieldInput('override', e.target.checked)"
                >
                Overwrite existing model file
            </label>
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
                label="Train"
                :on-click="validateAndSubmit"
                :disabled="disabled || (dirty && Object.keys(errors).length > 0)"
            />
        </template>
    </EscrModal>
</template>
<script>
import { mapActions, mapState } from "vuex";
import DropdownField from "../Dropdown/DropdownField.vue";
import EscrButton from "../Button/Button.vue";
import EscrModal from "../Modal/Modal.vue";
import TextField from "../TextField/TextField.vue";
import XIcon from "../Icons/XIcon/XIcon.vue";
import "../Common/Form.css";

export default {
    name: "EscrTrainModal",
    components: {
        DropdownField,
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
         * The list of existing models on the document. Should be an array of objects
         * with at least a name and pk for each model.
         */
        models: {
            type: Array,
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
         * Callback function for submitting the training task.
         */
        onSubmit: {
            type: Function,
            required: true,
        },
        /**
         * List of all transcription layers on this document.
         */
        transcriptions: {
            type: Array,
            required: true,
        },
    },
    data() {
        return {
            dirty: false,
        }
    },
    computed: {
        ...mapState({
            modalOpen: (state) => state.tasks.modalOpen,
            model: (state) => state.forms.train.model,
            modelName: (state) => state.forms.train.modelName,
            override: (state) => state.forms.train.override,
            transcription: (state) => state.forms.train.transcription,
        }),
        scope() {
            if (this.modalOpen.trainRecognizer) {
                return "Recognition";
            } else {
                return "Segmentation";
            }
        },
        modelOptions() {
            return this.models.map((model) => ({
                label: model.name,
                value: model.pk,
                selected: this.model.toString() === model.pk.toString(),
            }));
        },
        transcriptionOptions() {
            return this.transcriptions.map((trans) => ({
                label: trans.name,
                value: trans.pk,
                selected: this.transcription.toString() === trans.pk.toString(),
            }))
        },
        errors() {
            const errors = {};
            if (this.modalOpen.trainRecognizer && !this.transcription) {
                errors.transcription = ["Required field."];
            }
            if (!!this.modelName && !!this.model) {
                let err = "Cannot both create a new model and choose an existing model."
                errors.modelName = [err];
                errors.model = [err];
            } else if (!this.modelName && !this.model) {
                let err = "Must either create a new model or choose an existing model."
                errors.modelName = [err];
                errors.model = [err];
            }
            return errors;
        },
    },
    methods: {
        ...mapActions("forms", [
            "handleGenericInput",
        ]),
        handleTextFieldInput(field, value) {
            this.handleGenericInput({ field, value, form: "train" });
        },
        async validateAndSubmit() {
            this.dirty = true;
            if (!Object.keys(this.errors).length) {
                await this.onSubmit();
            }
        }
    }
};
</script>
