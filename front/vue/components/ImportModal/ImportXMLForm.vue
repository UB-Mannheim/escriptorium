<template>
    <div>
        <h3>Import segmentation and transcriptions from XML</h3>
        <span>
            Upload a single ALTO or PageXML file; alternatively, upload multiple files by
            compressing them into a ZIP file where all the XML files are at the root.
        </span>
        <fieldset class="xml-import">
            <input
                type="file"
                accept=".zip,.xml"
                :class="{ invalid: invalid['file'] }"
                @change="handleFileChange"
            >
            <TextField
                label="Transcription Name"
                help-text="The name of the resulting transcription layer."
                placeholder="Name"
                :invalid="invalid['layerName']"
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
import TextField from "../TextField/TextField.vue";

export default {
    name: "EscrImportXMLForm",
    components: {
        TextField,
    },
    props: {
        invalid: {
            type: Object,
            required: true,
        },
    },
    computed: {
        ...mapState({
            layerName: (state) => state.forms.import.layerName,
            overwrite: (state) => state.forms.import.overwrite,
        }),
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
        handleLayerNameInput(e) {
            this.handleGenericInput({
                form: "import", field: "layerName", value: e.target.value
            });
        },
        handleOverwriteChange(e) {
            this.handleGenericInput({
                form: "import", field: "overwrite", value: e.target.checked
            });
        },
    }
}
</script>
