<template>
    <div
        class="escr-form-field escr-checkbox-field"
        :aria-label="label"
    >
        <span
            v-if="labelVisible"
            class="escr-field-label"
        >
            {{ label }}<span
                v-if="required"
                class="escr-required"
            >*</span>
        </span>
        <label
            v-for="option in options"
            :key="option.value"
        >
            <input
                type="checkbox"
                :value="option.value"
                :checked="option.selected"
                @change="onChange"
            >
            <span>{{ option.label }}</span>
        </label>
        <span
            v-if="helpText"
            class="escr-help-text"
        >
            {{ helpText }}
        </span>
    </div>
</template>
<script>
import "./ArrayField.css";
import "../Common/Form.css";

export default {
    name: "EscrArrayField",
    props: {
        /**
         * Array of option objects, which should each have a label and value,
         * and a "selected" boolean.
         */
        options: {
            type: Array,
            required: true,
        },
        /**
         * Help text for the form field
         */
        helpText: {
            type: String,
            default: "",
        },
        /**
         * Label for the form field
         */
        label: {
            type: String,
            required: true,
        },
        /**
         * Callback for changing the selected checkboxes
         */
        onChange: {
            type: Function,
            required: true,
        },
        /**
         * Whether or not this field is required
         */
        required: {
            type: Boolean,
            default: false,
        },
        /**
         * Whether or not this field's label should be visible
         */
        labelVisible: {
            type: Boolean,
            default: true,
        },
    }
}
</script>
