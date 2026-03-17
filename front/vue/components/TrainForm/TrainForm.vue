<template>
    <div class="escr-model-training-form escr-card escr-card-padding">
        <div
            class="escr-form-field escr-model-type"
            role="group"
            aria-label="Model Type"
        >
            <span
                class="escr-field-label"
                aria-hidden="true"
            >
                Model Type
            </span>
            <EscrSegmentedButtonGroup
                name="model-type-toggle"
                :disabled="isSubmitting"
                :options="modelTypeOptions"
                :on-change-selection="onChangeModelType"
            />
        </div>
        <EscrTextField
            class="escr-model-name"
            label="Model Name"
            placeholder="Name your new model..."
            :disabled="form.override || isSubmitting"
            :value="form.model_name"
            :on-input="onInputName"
            :invalid="dirty && !isValid"
            :errors="dirty && !isValid ? ['A name is required unless overwriting'] : []"
            required
        />
        <EscrDropdownField
            class="escr-base-model"
            label="Base Model (optional)"
            title="Select a model to fine-tune, or leave blank to train from scratch."
            :disabled="isSubmitting"
            :options="availableModels"
            :on-change="onChangeBaseModel"
        />
        <label
            class="escr-form-field escr-overwrite"
            title="You must be the owner of the model to overwrite its file."
        >
            <input
                type="checkbox"
                :disabled="!form.model || isSubmitting"
                :checked="form.override"
                aria-describedby="overwrite-help"
                @change="onChangeOverride"
            >
            <span>Overwrite existing</span>
        </label>
        <span
            id="overwrite-help"
            class="sr-only"
        >
            You must be the owner of the base model to overwrite its file.
        </span>
        <EscrButton
            class="escr-train-btn"
            color="primary"
            label="Start Training"
            :disabled="!isValid || isSubmitting || !currentCollection.id || !currentCollection.items || currentCollection.items.length === 0"
            :on-click="submitTraining"
        />
        <div
            class="escr-global-errors escr-help-text error"
            role="alert"
            aria-live="polite"
        >
            <span
                v-if="!currentCollection.id &&
                    currentCollection.items &&
                    currentCollection.items.length > 0"
            >
                You must save this selection as a collection before you can train a model.
            </span>
            <span
                v-else-if="dirty &&
                    (!currentCollection.items || currentCollection.items.length === 0)"
            >
                You must select a collection of document parts in order to train a model.
            </span>
        </div>
    </div>
</template>

<script>
import { mapActions, mapState } from "vuex";
import EscrButton from "../../components/Button/Button.vue";
import EscrDropdownField from "../../components/Dropdown/DropdownField.vue";
// eslint-disable-next-line max-len
import EscrSegmentedButtonGroup from "../../components/SegmentedButtonGroup/SegmentedButtonGroup.vue";
import EscrTextField from "../../components/TextField/TextField.vue";
import "./TrainForm.css";

export default {
    components: {
        EscrButton,
        EscrDropdownField,
        EscrSegmentedButtonGroup,
        EscrTextField,
    },
    data() {
        return {
            dirty: false,
            isSubmitting: false,
            modelType: "recognizer",
            form: {
                model_name: "",
                model: null,
                override: false,
            },
        };
    },
    computed: {
        ...mapState("user", ["recognitionModels", "segmentationModels"]),
        ...mapState("collection", ["currentCollection"]),
        isValid() {
            // Require either a new name or an override of an existing model
            return (
                this.form.model_name || (this.form.model && this.form.override)
            );
        },
        availableModels() {
            const models =
                this.modelType === "recognizer"
                    ? this.recognitionModels
                    : this.segmentationModels;

            return models.map((m) => ({
                label: m.name,
                value: m.pk,
            }));
        },
        modelTypeOptions() {
            return [
                {
                    label: "Recognition",
                    value: "recognizer",
                    selected: this.modelType === "recognizer",
                },
                {
                    label: "Segmentation",
                    value: "segmenter",
                    selected: this.modelType === "segmenter",
                },
            ];
        },
    },
    mounted() {
        this.fetchRecognizeModels();
        this.fetchSegmentModels();
    },
    methods: {
        ...mapActions("user", ["fetchRecognizeModels", "fetchSegmentModels"]),
        /**
         * Submit model training payload to the backend
         */
        async submitTraining() {
            this.isSubmitting = true;
            try {
                // rm null/empty values from payload so API doesn't reject them
                const payload = {};
                if (this.form.model_name) payload.model_name = this.form.model_name;
                if (this.form.model) payload.model = this.form.model;
                if (this.form.override) payload.override = this.form.override;

                await this.$store.dispatch("collection/trainModel", {
                    modelType: this.modelType,
                    payload,
                });

                this.$store.dispatch("alerts/add", {
                    color: "success",
                    message: "Training job successfully queued!",
                });
            } catch (error) {
                this.$store.dispatch("alerts/addError", error);
            } finally {
                this.isSubmitting = false;
            }
        },
        /**
         * Input handler for model type toggle
         */
        onChangeModelType(val) {
            this.modelType = val;
            this.form.model = null;
            this.form.override = false;
        },
        /**
         * Input handler for name text field
         */
        onInputName(e) {
            this.form.model_name = e.target.value;
            this.dirty = true;
        },
        /**
         * Input handler for base model selection
         */
        onChangeBaseModel(e) {
            this.form.model = e.target.value;
            this.dirty = true;
            if (!this.form.model) this.form.override = false;
        },
        /**
         * Input handler for override checkbox
         */
        onChangeOverride(e) {
            this.form.override = e.target.checked;
            this.dirty = true;
            if (this.form.override) {
                this.form.model_name = "";
            }
        },
    },
};
</script>
