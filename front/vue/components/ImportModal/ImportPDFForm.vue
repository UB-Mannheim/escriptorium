<template>
    <div>
        <h3>Import images from a PDF document</h3>
        <span>Import images by uploading a single PDF with one image per page.</span>
        <fieldset class="pdf-import">
            <input
                type="file"
                accept=".pdf"
                @change="handleFileChange"
            >
        </fieldset>
    </div>
</template>
<script>
import { mapActions } from "vuex";

export default {
    name: "EscrImportPDFForm",
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
    }
}
</script>
