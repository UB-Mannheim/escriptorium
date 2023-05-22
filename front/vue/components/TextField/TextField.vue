<template>
    <label class="escr-text-field escr-form-field">
        <span
            v-if="labelVisible"
            class="escr-field-label"
        >
            {{ label }}<span
                v-if="required"
                class="escr-required"
            >*</span>
        </span>
        <input
            type="text"
            :placeholder="placeholder"
            :aria-label="label"
            :value="value"
            :disabled="disabled"
            :name="name"
            @input="onInput"
        >
        <span
            v-if="helpText"
            class="escr-help-text"
        >
            {{ helpText }}
        </span>
    </label>
</template>
<script>
import "./TextField.css";
import "../Common/Form.css";
export default {
    name: "EscrTextField",
    props: {
        disabled: {
            type: Boolean,
            default: false,
        },
        /**
         * Event handler for the text input
         */
        onInput: {
            type: Function,
            required: true,
        },
        /**
         * Placeholder text (optional)
         */
        placeholder: {
            type: String,
            default: "",
        },
        /**
         * Help text (optional)
         */
        helpText: {
            type: String,
            default: "",
        },
        /**
         * Label text
         */
        label: {
            type: String,
            required: true,
        },
        /**
         * Whether or not the label is visible (if not, it is just used for
         * assistive technologies such as screen readers)
         */
        labelVisible: {
            type: Boolean,
            default: true,
        },
        /**
         * Optional input name, which is necessary if using in an HTML form.
         */
        name: {
            type: String,
            default: "",
        },
        /**
         * Whether or not this field is required in the form.
         */
        required: {
            type: Boolean,
            default: false,
        },
        /**
         * Current value.
         */
        value: {
            type: String,
            default: "",
        },
    },
}
</script>
