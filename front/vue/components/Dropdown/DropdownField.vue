<template>
    <label class="escr-dropdown-field escr-form-field">
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
        <EscrDropdown
            :label="label"
            :disabled="disabled"
            :options="options"
            :on-change="onChange"
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
import EscrDropdown from "./Dropdown.vue";
import "./DropdownField.css";
import "../Common/Form.css";
export default {
    name: "EscrDropdownField",
    components: { EscrDropdown },
    props: {
        /**
         * Boolean indicating if the form field is disabled
         */
        disabled: {
            type: Boolean,
            default: false,
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
         * Whether or not the label is visible (if not, it is just used for
         * assistive technologies such as screen readers)
         */
        labelVisible: {
            type: Boolean,
            default: true,
        },
        /**
         * Event handler for the select change
         */
        onChange: {
            type: Function,
            required: true,
        },
        /**
         * List of options, each of which should be an object:
         * {
         *     value: String,
         *     label: String,
         *     selected: Boolean,
         * }
         */
        options: {
            type: Array,
            required: true,
        },
        /**
         * Whether or not this field is required in the form.
         */
        required: {
            type: Boolean,
            default: false,
        },
        /**
         * Array of error strings.
         */
        errors: {
            type: Array,
            default: () => [],
        },
    },
}
</script>
