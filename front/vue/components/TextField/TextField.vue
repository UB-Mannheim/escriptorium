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
        <input
            v-if="!textarea"
            type="text"
            :placeholder="placeholder"
            :aria-label="label"
            :value="value"
            :disabled="disabled"
            :name="name"
            :maxlength="maxLength"
            :invalid="invalid"
            @input="onInput"
            @keydown="onKeydown"
        >
        <textarea
            v-else
            :placeholder="placeholder"
            :aria-label="label"
            :value="value"
            :disabled="disabled"
            :name="name"
            :maxlength="maxLength"
            :invalid="invalid"
            @input="onInput"
            @keydown="onKeydown"
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
         * Event handler for pressing a key
         */
        onKeydown: {
            type: Function,
            default: () => {},
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
         * Invalid attribute for html-based form validation (optional)
         */
        invalid: {
            type: Boolean,
            default: false,
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
         * Optional maximum length of the text field.
         */
        maxLength: {
            type: Number,
            default: undefined,
        },
        /**
         * Whether or not the input should be a textarea (as opposed to input type="text").
         */
        textarea: {
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
