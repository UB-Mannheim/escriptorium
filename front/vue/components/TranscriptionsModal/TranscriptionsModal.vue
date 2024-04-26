<template>
    <EscrModal class="escr-transcription-management">
        <template #modal-header>
            <h2>Transcriptions</h2>
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
            <EscrTable
                item-key="pk"
                :headers="headers"
                :items="sortedTranscriptions.filter((t) => !t.archived)"
                :on-edit="onEditTranscription"
                :on-sort="sortTranscriptions"
                :disabled="disabled"
                :editing-key="editing && editing.pk.toString()"
            >
                <template #actions="{ item }">
                    <!-- edit button -->
                    <EscrButton
                        v-if="!editing || editing.pk !== item.pk"
                        class="escr-transcription-edit-icon"
                        size="small"
                        color="text"
                        :on-click="() => { editing = item }"
                    >
                        <template #button-icon>
                            <PencilIcon />
                        </template>
                    </EscrButton>
                    <!-- editing confirm/cancel buttons -->
                    <EscrButton
                        v-else-if="editing && editing.pk === item.pk"
                        class="escr-transcription-edit-icon"
                        size="small"
                        color="text"
                        :on-click="onConfirmEditTranscription"
                    >
                        <template #button-icon>
                            <CheckCircleIcon />
                        </template>
                    </EscrButton>
                    <EscrButton
                        v-if="editing && editing.pk === item.pk"
                        class="escr-transcription-edit-icon"
                        size="small"
                        color="text"
                        :on-click="onCancelEditTranscription"
                    >
                        <template #button-icon>
                            <XCircleIcon />
                        </template>
                    </EscrButton>
                    <!-- delete -->
                    <EscrButton
                        size="small"
                        color="text"
                        :on-click="() => openDeleteModal(item)"
                        :disabled="disabled"
                        aria-label="Delete transcription"
                    >
                        <template #button-icon>
                            <TrashIcon />
                        </template>
                    </EscrButton>
                </template>
            </EscrTable>
        </template>
        <template #modal-actions>
            <!-- only show save/cancel if changes have been made, otherwise it's confusing -->
            <EscrButton
                v-if="dirty"
                color="outline-primary"
                label="Cancel"
                :on-click="onCancel"
                :disabled="disabled"
            />
            <EscrButton
                v-if="dirty"
                color="primary"
                label="Save"
                :on-click="onSave"
                :disabled="disabled || !!editing"
            />
        </template>
    </EscrModal>
</template>
<script>
import { mapActions, mapState } from "vuex";
import CheckCircleIcon from "../Icons/CheckCircleIcon/CheckCircleIcon.vue";
import EscrButton from "../Button/Button.vue";
import EscrModal from "../Modal/Modal.vue";
import EscrTable from "../Table/Table.vue";
import PencilIcon from "../Icons/PencilIcon/PencilIcon.vue";
import TrashIcon from "../Icons/TrashIcon/TrashIcon.vue";
import XCircleIcon from "../Icons/XCircleIcon/XCircleIcon.vue";
import XIcon from "../Icons/XIcon/XIcon.vue";
import "./TranscriptionsModal.css";

export default {
    name: "EscrTranscriptionsModal",
    components: {
        CheckCircleIcon,
        EscrButton,
        EscrModal,
        EscrTable,
        PencilIcon,
        TrashIcon,
        XCircleIcon,
        XIcon,
    },
    props: {
        /**
         * If true, all buttons and form fields are disabled
         */
        disabled: {
            type: Boolean,
            required: true,
        },
        /**
         * Callback for canceling changes (by closing modal or clicking the cancel button)
         */
        onCancel: {
            type: Function,
            required: true,
        },
        /**
         * Callback for clicking the save button
         */
        onSave: {
            type: Function,
            required: true,
        },
    },
    data() {
        return {
            // keep track of internal editing state (will be a single transcription)
            editing: null,
            // keep track of table sorting (it's frontend only)
            sortState: { field: null, direction: 0 },
        };
    },
    computed: {
        ...mapState({
            transcriptions: (state) => state.transcriptions.all,
            formTranscriptions: (state) => state.forms.transcriptionManagement.transcriptions,
        }),
        // Boolean indicating whether or not transcriptions have been edited
        dirty() {
            return this.transcriptions.map((transcription) => {
                // match form transcription to state transcription by pk
                const formData = this.formTranscriptions.find((ft) => ft.pk === transcription.pk);
                // check if any of the values are different using key/value pairs
                return formData &&
                    Object.entries(formData).some(([k, v]) => v !== transcription[k]);
            }).some((edited) => edited === true);
        },
        // Table headers for transcriptions list
        headers() {
            return [
                { label: "Name", value: "name", sortable: true, editable: true },
                {
                    label: "Date Created",
                    value: "created_at",
                    sortable: true,
                    format: (val) => new Date(val).toLocaleDateString(
                        undefined,
                        { year: "numeric", month: "long", day: "numeric" },
                    ),
                },
                { label: "Comments", value: "comments", sortable: false, editable: true },
            ];
        },
        // transcriptions sorted by sort state
        sortedTranscriptions() {
            if (this.sortState.direction !== 0 && this.sortState.field) {
                return this.formTranscriptions.toSorted((a, b) => {
                    if (a[this.sortState.field] < b[this.sortState.field]) {
                        return -1 * this.sortState.direction;
                    } else return this.sortState.direction;
                });
            } else return this.formTranscriptions;
        },
    },
    methods: {
        ...mapActions("forms", ["handleGenericInput"]),
        ...mapActions("transcriptions", ["openDeleteModal"]),
        /**
         * Sort transcriptions using component's local data to keep track of sort state
         */
        sortTranscriptions({ field, direction }) {
            this.sortState = { field, direction };
        },
        /**
         * On input, update form state for transcription edits
         */
        onEditTranscription({ field, value }) {
            const formClone = structuredClone(this.formTranscriptions);
            formClone.forEach((item) => {
                if (item?.pk === this.editing.pk) {
                    item[field] = value;
                }
            });
            this.handleGenericInput({
                form: "transcriptionManagement", field: "transcriptions", value: formClone
            });
        },
        /**
         * On cancelling an edit, reset form state back to original values for ONLY the
         * transcription that was cancelled
         */
        onCancelEditTranscription() {
            const formClone = structuredClone(this.formTranscriptions);
            formClone.forEach((item) => {
                if (item?.pk === this.editing.pk) {
                    // reset editable values
                    Object
                        .keys(item)
                        .filter((field) => this.headers.find(
                            (header) => header.value === field
                        )?.editable === true)
                        .forEach((field) => item[field] = this.editing[field]);
                }
            });
            this.handleGenericInput({
                form: "transcriptionManagement", field: "transcriptions", value: formClone
            });
            // reset editing to null
            this.editing = null;
        },
        /**
         * On confirming an edit, since the form values were already modified in
         * onEditTranscription, just turn off editing state
         */
        onConfirmEditTranscription() {
            // reset editing to null
            this.editing = null;
        },
    }
}
</script>
