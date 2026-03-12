<template>
    <div class="collection-training-form">
        <h2>Train Model</h2>
        <div class="escr-form-field">
            <span class="escr-label">Model Type</span>
            <EscrSegmentedButtonGroup
                name="model-type-toggle"
                :disabled="isSubmitting"
                :options="modelTypeOptions"
                :on-change-selection="(val) => (modelType = val)"
            />
        </div>
        <EscrTextField
            label="Model Name"
            placeholder="Name your new model..."
            :disabled="form.override || isSubmitting"
            :value="form.model_name"
            :on-input="(e) => (form.model_name = e.target.value)"
            :invalid="!form.model_name && !form.model"
            :errors="
                !form.model_name && !form.model
                    ? ['A name or a base model is required']
                    : []
            "
            required
        />
        <EscrDropdownField
            label="Base Model (optional)"
            help-text="You may select an existing model to fine-tune. If left unselected,
            the model will be trained from scratch."
            :disabled="isSubmitting"
            :options="availableModels"
            :on-change="(e) => (form.model = e.target.value)"
        />
        <label class="escr-form-field">
            <input
                type="checkbox"
                :disabled="!form.model || isSubmitting"
                :checked="form.override"
                @change="(e) => (form.override = e.target.checked)"
            >
            Overwrite existing model file (you must be the owner)
        </label>
        <EscrButton
            color="primary"
            label="Start Training"
            :disabled="!isValid || isSubmitting"
            :on-click="submitTraining"
        />
    </div>
</template>

<script>
import { mapActions, mapState } from "vuex";
import EscrButton from "../../components/Button/Button.vue";
import EscrDropdownField from "../../components/Dropdown/DropdownField.vue";
// eslint-disable-next-line max-len
import EscrSegmentedButtonGroup from "../../components/SegmentedButtonGroup/SegmentedButtonGroup.vue";
import EscrTextField from "../../components/TextField/TextField.vue";

export default {
    components: {
        EscrButton,
        EscrDropdownField,
        EscrSegmentedButtonGroup,
        EscrTextField,
    },
    data() {
        return {
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
                await this.$store.dispatch("collection/trainModel", {
                    modelType: this.modelType,
                    payload: this.form,
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
    },
};
</script>
