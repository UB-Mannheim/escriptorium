<template>
    <label class="escr-text-field escr-form-field">
        <span v-if="labelVisible">
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
            @input="onInput"
        >
    </label>
</template>
<script>
import "./TextField.css";
export default {
    name: "EscrTextField",
    props: {
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
