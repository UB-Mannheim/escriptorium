<template>
    <label>
        <span v-if="labelVisible">
            {{ label }}
        </span>
        <input
            type="text"
            :class="classes"
            :placeholder="placeholder"
            :aria-label="label"
            @input="onInput"
        />
    </label>
</template>
<script>
import './TextField.css';
export default {
    name: 'escr-text-field',
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
    },
    computed: {
        classes() {
            return {
                'escr-text-field': true,
            };
        },
    },
}
</script>
