<template>
    <EscrModal class="escr-download-archive-modal">
        <template #modal-header>
            <h2>{{ $gettext("Download Archive") }} {{ scope }}</h2>
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
            <p class="escr-archive-intro">
                {{ introText }}
            </p>
            <div class="escr-form-field">
                <label v-translate>Archive format</label>
                <select
                    :value="archiveFormat"
                    @change="handleArchiveFormatChange"
                >
                    <option value="zip">
                        ZIP (.zip)
                    </option>
                    <option value="tar.gz">
                        Gzipped Tar (.tar.gz)
                    </option>
                </select>
            </div>
            <div class="escr-form-field escr-checkbox-field">
                <label>
                    <input
                        type="checkbox"
                        :checked="includeImages"
                        @change="handleIncludeImagesChange"
                    >
                    {{ $gettext("Include images") }}
                </label>
            </div>
        </template>
        <template #modal-actions>
            <EscrButton
                color="outline-primary"
                :label="$gettext('Cancel')"
                :on-click="onCancel"
                :disabled="disabled"
            />
            <EscrButton
                color="primary"
                :label="$gettext('Download')"
                :on-click="onSubmit"
                :disabled="disabled"
            />
        </template>
    </EscrModal>
</template>
<script>
import { mapActions, mapState } from "vuex";
import EscrButton from "../Button/Button.vue";
import EscrModal from "../Modal/Modal.vue";
import XIcon from "../Icons/XIcon/XIcon.vue";
import "../Common/Form.css";

export default {
    name: "EscrDownloadArchiveModal",
    components: {
        EscrButton,
        EscrModal,
        XIcon,
    },
    props: {
        disabled: { type: Boolean, required: true },
        scope: { type: String, required: true },
        onSubmit: { type: Function, required: true },
        onCancel: { type: Function, required: true },
    },
    computed: {
        ...mapState({
            archiveFormat: (state) => state.forms.downloadArchive.archiveFormat,
            includeImages: (state) => state.forms.downloadArchive.includeImages,
        }),
        scopeNoun() {
            // "Document" -> "document", "Elements" -> "selection"
            if (this.scope === "Elements") return this.$gettext("selection");
            return this.scope.toLowerCase() || this.$gettext("document");
        },
        introText() {
            return this.$gettextInterpolate(
                this.$gettext("Exports %{scope} as a full JSON archive."),
                { scope: this.scopeNoun },
            );
        },
    },
    methods: {
        ...mapActions("forms", ["handleGenericInput"]),
        handleIncludeImagesChange(e) {
            this.handleGenericInput({
                form: "downloadArchive",
                field: "includeImages",
                value: e.target.checked,
            });
        },
        handleArchiveFormatChange(e) {
            this.handleGenericInput({
                form: "downloadArchive",
                field: "archiveFormat",
                value: e.target.value,
            });
        },
    },
};
</script>
<style scoped>
.escr-download-archive-modal .escr-archive-intro {
    margin: 0 0 16px;
    color: #495057;
    font-size: 0.9rem;
    line-height: 1.5;
}
</style>
