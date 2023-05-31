<template>
    <div>
        <h3>Import images, segmentation and transcriptions described by METS</h3>
        <fieldset>
            <SegmentedButtonGroup
                color="secondary"
                name="mets-type"
                :on-change-selection="handleMetsTypeChange"
                :options="metsOptions"
            />
            <div
                v-if="metsType === 'file'"
            >
                <input
                    type="file"
                    accept=".zip"
                    @change="handleFileChange"
                >
                <span class="escr-help-text">
                    A single ZIP archive described by a METS file contained inside it.
                </span>
            </div>
            <div v-else>
                <TextField
                    label="Remote METS URI"
                    placeholder="Enter METS file URI"
                    :label-visible="false"
                    :value="metsUri"
                    :on-input="handleMetsUriInput"
                />
            </div>
            <TextField
                label="Transcription Name"
                help-text="The name of the resulting transcription layer."
                placeholder="Name"
                :value="layerName"
                :on-input="handleLayerNameInput"
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
                    Overwriting destroys existing regions, lines and any bound transcriptions
                    before importing.
                </span>
            </div>
        </fieldset>
    </div>
</template>
<script>
import { mapActions, mapState } from "vuex";
import SegmentedButtonGroup from "../SegmentedButtonGroup/SegmentedButtonGroup.vue";
import TextField from "../TextField/TextField.vue";

export default {
    name: "EscrImportMETSForm",
    components: {
        SegmentedButtonGroup,
        TextField,
    },
    computed: {
        ...mapState({
            layerName: (state) => state.forms.import.layerName,
            metsType: (state) => state.forms.import.metsType,
            metsUri: (state) => state.forms.import.metsUri,
            overwrite: (state) => state.forms.import.overwrite,
        }),
        metsOptions() {
            return [
                { value: "url", label: "Enter URL", selected: this.metsType === "url" },
                { value: "file", label: "Upload file", selected: this.metsType === "file" }
            ];
        },
    },
    methods: {
        ...mapActions("forms", [
            "handleGenericInput",
        ]),
        handleFileChange(e) {
            this.handleGenericInput({
                form: "import",
                field: "uploadFile",
                value: e.target.files[0],
            });
        },
        handleMetsTypeChange(value) {
            this.handleGenericInput({
                form: "import", field: "metsType", value
            });
        },
        handleLayerNameInput(e) {
            this.handleGenericInput({
                form: "import", field: "layerName", value: e.target.value
            });
        },
        handleMetsUriInput(e) {
            this.handleGenericInput({
                form: "import", field: "metsUri", value: e.target.value
            });
        },
        handleOverwriteChange(e) {
            this.handleGenericInput({
                form: "import", field: "overwrite", value: e.target.checked
            });
        },
    },
}
</script>
