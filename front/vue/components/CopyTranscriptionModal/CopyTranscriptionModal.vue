<template>
    <EscrModal class="escr-copy-transcription-modal">
        <template #modal-header>
            <h2>Copy transcription layer</h2>
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
                :message="`Copies “${sourceName}” into the destination layer, for this page only.`"
            />
            <AutocompleteField
                label="Copy to"
                :disabled="disabled"
                help-text="Select an existing layer or enter a new name."
                :option-groups="transcriptionOptionGroups"
                :on-change="handleTargetInput"
                :allow-custom-value="true"
                placeholder="Select or enter layer name"
                required
            />
            <EscrAlert
                v-if="targetIsExisting"
                color="warning"
                :message="overwriteWarning"
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
                label="Copy"
                :on-click="onSubmit"
                :disabled="disabled || invalid"
            />
        </template>
    </EscrModal>
</template>
<script>
import { mapActions, mapState } from "vuex";
import AutocompleteField from "../AutocompleteDropdown/AutocompleteField.vue";
import EscrAlert from "../Alert/Alert.vue";
import EscrButton from "../Button/Button.vue";
import EscrModal from "../Modal/Modal.vue";
import XIcon from "../Icons/XIcon/XIcon.vue";
import "../Common/Form.css";

export default {
    name: "EscrCopyTranscriptionModal",
    components: {
        AutocompleteField,
        EscrAlert,
        EscrButton,
        EscrModal,
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
         * Callback function for clicking "cancel".
         */
        onCancel: {
            type: Function,
            required: true,
        },
        /**
         * Callback for submitting the copy. Called with { target } for an existing layer
         * or { targetName } for a new one.
         */
        onCopy: {
            type: Function,
            required: true,
        },
    },
    computed: {
        ...mapState({
            transcriptions: (state) => state.transcriptions.all,
            selectedTranscription: (state) => state.transcriptions.selectedTranscription,
            target: (state) => state.forms.copyTranscription.target,
        }),
        // the layer currently displayed in the panel, i.e. the one being copied
        source() {
            return this.transcriptions.find(
                (t) => parseInt(t.pk) === parseInt(this.selectedTranscription),
            );
        },
        sourceName() {
            return this.source ? this.source.name : "";
        },
        // every non-archived layer except the source, which can't be its own destination
        selectableTranscriptions() {
            return this.transcriptions.filter(
                (t) => !t.archived
                    && parseInt(t.pk) !== parseInt(this.selectedTranscription),
            );
        },
        // the existing layer matching what's in the field, if any
        matchedTranscription() {
            return this.selectableTranscriptions.find((t) => t.name === this.target);
        },
        targetIsExisting() {
            return !!this.matchedTranscription;
        },
        overwriteWarning() {
            return "Lines already transcribed in this layer will be overwritten. " +
                "Their previous content is kept in each line's history.";
        },
        invalid() {
            // can't copy onto the source layer, even by typing its name
            return !this.target || this.target === this.sourceName;
        },
        /**
         * Format existing transcription layers as options
         */
        transcriptionOptionGroups() {
            const options = this.selectableTranscriptions.map((transcription) => ({
                label: transcription.name,
                value: transcription.name,
                selected: this.target === transcription.name,
            }));

            return options.length > 0
                ? [{ label: "Existing Layers", options }]
                : [];
        },
    },
    methods: {
        ...mapActions("forms", ["handleGenericInput"]),
        handleTargetInput(e) {
            this.handleGenericInput({
                form: "copyTranscription", field: "target", value: e.target.value,
            });
        },
        onSubmit() {
            if (this.invalid) return;
            if (this.matchedTranscription) {
                this.onCopy({ target: this.matchedTranscription.pk });
            } else {
                this.onCopy({ targetName: this.target });
            }
        },
    },
};
</script>
