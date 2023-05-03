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
                label="Cancel"
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
        bodyText: {
            type: String,
            required: true,
        },
        cannotUndo: {
            type: Boolean,
            default: true,
        },
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
        confirmVerb: {
            type: String,
            default: "Submit",
        },
        disabled: {
            type: Boolean,
            default: false,
        },
        icon: {
            type: Object,
            default: () => WarningIcon,
            required: false,
        },
        onCancel: {
            type: Function,
            required: true,
        },
        onConfirm: {
            type: Function,
            required: true,
        },
        title: {
            type: String,
            required: true,
        },
    }
}
</script>
