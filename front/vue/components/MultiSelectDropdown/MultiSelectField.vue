<template>
    <label class="escr-multiselect-field escr-form-field">
        <span
            v-if="labelVisible"
            class="escr-field-label"
        >
            {{ label }}<span
                v-if="required"
                class="escr-required"
            >*</span>
        </span>
        <ul
            v-if="errors && errors.length > 0"
            class="escr-field-errors"
        >
            <li
                v-for="(error, i) in errors"
                :key="`error-${i}`"
                class="escr-help-text escr-error-text"
            >
                {{ error }}
            </li>
        </ul>
        <EscrMultiSelectDropdown
            :label="label"
            :disabled="disabled"
            :options="options"
            :on-change="onChange"
            :placeholder="placeholder"
        />
        <span
            v-if="helpText"
            class="escr-help-text"
        >
            {{ helpText }}
        </span>
    </label>
</template>
<script>
import EscrMultiSelectDropdown from "./MultiSelectDropdown.vue";
import "../Common/Form.css";

export default {
    name: "EscrMultiSelectField",
    components: { EscrMultiSelectDropdown },
    props: {
        /**
         * Boolean indicating if the form field is disabled
         */
        disabled: {
            type: Boolean,
            default: false,
        },
        /**
         * Array of error messages to display
         */
        errors: {
            type: Array,
            default: () => [],
        },
        /**
         * Optional help text for the form field
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
         * Whether or not the label is visible
         */
        labelVisible: {
            type: Boolean,
            default: true,
        },
        /**
         * Event handler for the change event
         */
        onChange: {
            type: Function,
            required: true,
        },
        /**
         * List of options
         */
        options: {
            type: Array,
            required: true,
        },
        /**
         * Placeholder text
         */
        placeholder: {
            type: String,
            default: "Select items...",
        },
        /**
         * Whether or not this field is required in the form.
         */
        required: {
            type: Boolean,
            default: false,
        },
    },
};
</script>
