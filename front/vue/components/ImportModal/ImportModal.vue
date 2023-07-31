<template>
    <EscrModal
        class="escr-import-modal"
    >
        <template #modal-header>
            <h2>Import Elements</h2>
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
            <ul class="escr-import-modes">
                <li :class="importMode === 'images' ? 'selected' : ''">
                    <button @click="() => setImportMode('images')">
                        <ImagesIcon />
                        <span>Images</span>
                    </button>
                </li>
                <li :class="importMode === 'pdf' ? 'selected' : ''">
                    <button @click="() => setImportMode('pdf')">
                        <PDFIcon />
                        <span>PDF</span>
                    </button>
                </li>
                <li :class="importMode === 'iiif' ? 'selected' : ''">
                    <button @click="() => setImportMode('iiif')">
                        <IIIFIcon />
                        <span>IIIF</span>
                    </button>
                </li>
                <li :class="importMode === 'mets' ? 'selected' : ''">
                    <button @click="() => setImportMode('mets')">
                        <METSIcon />
                        <span>METS</span>
                    </button>
                </li>
                <li :class="importMode === 'xml' ? 'selected' : ''">
                    <button @click="() => setImportMode('xml')">
                        <XMLIcon />
                        <span>XML / ZIP</span>
                    </button>
                </li>
            </ul>
            <component
                :is="currentComponent"
                :invalid="invalid"
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
                label="Upload"
                :on-click="handleSubmit"
                :disabled="disabled"
            />
        </template>
    </EscrModal>
</template>
<script>
import { mapActions, mapState } from "vuex";
import EscrButton from "../Button/Button.vue";
import EscrModal from "../Modal/Modal.vue";
import ImportIIIFForm from "./ImportIIIFForm.vue";
import ImportImagesForm from "./ImportImagesForm.vue";
import ImportMETSForm from "./ImportMETSForm.vue";
import ImportPDFForm from "./ImportPDFForm.vue";
import ImportXMLForm from "./ImportXMLForm.vue";
import IIIFIcon from "../Icons/IIIFIcon/IIIFIcon.vue";
import ImagesIcon from "../Icons/ImagesIcon/ImagesIcon.vue";
import METSIcon from "../Icons/METSIcon/METSIcon.vue";
import PDFIcon from "../Icons/PDFIcon/PDFIcon.vue";
import XIcon from "../Icons/XIcon/XIcon.vue";
import XMLIcon from "../Icons/XMLIcon/XMLIcon.vue";
import "./ImportModal.css";

export default {
    name: "EscrImportModal",
    components: {
        EscrButton,
        EscrModal,
        IIIFIcon,
        ImagesIcon,
        METSIcon,
        PDFIcon,
        XIcon,
        XMLIcon,
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
         * Callback function for submitting the import task.
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
    data() {
        return {
            invalid: {},
        };
    },
    computed: {
        ...mapState({
            iiifUri: (state) => state.forms.import.iiifUri,
            importMode: (state) => state.forms.import.mode,
            layerName: (state) => state.forms.import.layerName,
            metsUri: (state) => state.forms.import.metsUri,
            metsType: (state) => state.forms.import.metsType,
            uploadFile: (state) => state.forms.import.uploadFile,
        }),
        currentComponent() {
            switch (this.importMode) {
                case "images":
                default:
                    return ImportImagesForm;
                case "pdf":
                    return ImportPDFForm;
                case "iiif":
                    return ImportIIIFForm;
                case "mets":
                    return ImportMETSForm;
                case "xml":
                    return ImportXMLForm;
            }
        },
    },
    methods: {
        ...mapActions("forms", [
            "handleGenericInput",
        ]),
        setImportMode(mode) {
            this.handleGenericInput({ form: "import", field: "mode", value: mode })
        },
        recalculateInvalid() {
            let invalid = {};
            switch (this.importMode) {
                case "images":
                default:
                    break;
                case "pdf":
                    invalid = { file: !this.uploadFile };
                    break;
                case "iiif":
                    invalid = { iiifUri: !this.iiifUri };
                    break;
                case "mets":
                    invalid = { layerName: !this.layerName };
                    invalid =  this.metsType === "local"
                        ? { ...invalid, file: !this.uploadFile }
                        : { ...invalid, metsUri: !this.metsUri };
                    break;
                case "xml":
                    invalid = {
                        file: !this.uploadFile,
                        layerName: !this.layerName,
                    };
                    break;
            }
            this.invalid = invalid;
            return invalid;
        },
        handleSubmit() {
            const invalid = this.recalculateInvalid();
            if (Object.keys(invalid).some((key) => invalid[key] === true)) {
                // if any are invalid, don't submit, just show red
                console.log(invalid);
            } else {
                // otherwise, submit
                this.onSubmit();
            }
        },
    },
}
</script>
