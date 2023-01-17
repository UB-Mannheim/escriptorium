<template>
    <input
        type="text"
        :class="classes"
        :placeholder="placeholder"
        :aria-label="label"
        @input="onInput"
    />
</template>
<script>
import './TextField.css';
export default {
    name: 'escr-text-field',
    props: {
        onInput: {
            type: Function,
            required: true,
        },
        placeholder: {
            type: String,
        },
        label: {
            type: String,
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
