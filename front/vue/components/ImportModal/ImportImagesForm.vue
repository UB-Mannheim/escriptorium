<template>
    <div>
        <h3>Import images</h3>
        <ImageDropzone
            id="escr-drop-zone"
            :options="{
                ...dropzoneOptions,
                url: imageUploadURL,
                headers: { 'X-Csrftoken': getCsrfToken },
            }"
            :use-custom-slot="true"
        >
            <UploadIcon />
            <h4>Drag and drop files here</h4>
            <p>Files supported: JPG, PNG, TIFF</p>
            <p>or</p>
            <button
                type="button"
                class="escr-button escr-button--large escr-button--primary"
            >
                Choose files
            </button>
        </ImageDropzone>
    </div>
</template>

<script>
import { mapState } from "vuex";
import UploadIcon from "../Icons/UploadIcon/UploadIcon.vue";
import ImageDropzone from "vue2-dropzone";
import "vue2-dropzone/dist/vue2Dropzone.min.css";

export default {
    name: "EscrImportImagesForm",
    components: {
        ImageDropzone,
        UploadIcon,
    },
    props: {
        invalid: {
            type: Object,
            required: true,
        },
    },
    data: function() {
        return {
            dropzoneOptions: {
                acceptedFiles: "image/jpeg,image/png,image/tiff",
                parallelUploads: 1,
                paramName: "image",
                timeout: 0,
            }
        };
    },
    computed: {
        ...mapState({
            documentId: (state) => state.document.id,
        }),
        /**
         * Use the document ID from vuex store state to get the parts upload URL.
         */
        imageUploadURL() {
            return `/api/documents/${this.documentId}/parts/`;
        },
        getCsrfToken() {
            return document.cookie.match("(^|;)\\s*" + "csrftoken" + "\\s*=\\s*([^;]+)")?.pop()
        }
    },
}
</script>
