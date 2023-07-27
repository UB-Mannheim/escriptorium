<template>
    <EscrModal class="escr-confirm-modal">
        <template #modal-header>
            <h2 :class="`confirm-header--${color}`">
                <component
                    :is="icon"
                    v-if="icon"
                />{{ title }}
            </h2>
        </template>
        <template #modal-content>
            <h3>{{ bodyText }}</h3>
            <p v-if="cannotUndo">
                You cannot undo this action.
            </p>
        </template>
        <template #modal-actions>
            <EscrButton
                color="outline-text"
                :label="cancelVerb"
                :on-click="onCancel"
                :disabled="disabled"
            />
            <EscrButton
                :color="color"
                :label="confirmVerb"
                :on-click="onConfirm"
                :disabled="disabled"
            />
        </template>
    </EscrModal>
</template>
<script>
import EscrButton from "../Button/Button.vue";
import EscrModal from "../Modal/Modal.vue";
import WarningIcon from "../Icons/WarningIcon/WarningIcon.vue";
import "./ConfirmModal.css";

export default {
    name: "EscrConfirmModal",
    components: {
        EscrButton,
        EscrModal,
    },
    props: {
        /**
         * The text to appear underneath the header, explaining the choices.
         */
        bodyText: {
            type: String,
            required: true,
        },
        /**
         * The word to display on the cancel button, such as "Cancel" or "No".
         */
        cancelVerb: {
            type: String,
            default: "Cancel",
        },
        /**
         * Whether or not to display the "cannot undo this action" message, defaults to true.
         */
        cannotUndo: {
            type: Boolean,
            default: true,
        },
        /**
         * Color of the submit button and the header icon.
         */
        color: {
            type: String,
            default: "danger",
            validator: function (value) {
                return [
                    "primary",
                    "secondary",
                    "tertiary",
                    "danger",
                    "text",
                ].includes(value);
            },
        },
        /**
         * The verb to display on the submit/confirm button, such as "Delete" or "Submit".
         */
        confirmVerb: {
            type: String,
            default: "Submit",
        },
        /**
         * Whether or not the submit/cancel buttons are disabled.
         */
        disabled: {
            type: Boolean,
            default: false,
        },
        /**
         * The icon component to appear in the modal header. Must be a Vue Component.
         */
        icon: {
            type: Object,
            default: () => WarningIcon,
            required: false,
        },
        /**
         * Callback function for clicking the cancel button.
         */
        onCancel: {
            type: Function,
            required: true,
        },
        /**
         * Callback function for clicking the confirmation button.
         */
        onConfirm: {
            type: Function,
            required: true,
        },
        /**
         * Text to appear in the header of the modal.
         */
        title: {
            type: String,
            required: true,
        },
    }
}
</script>
