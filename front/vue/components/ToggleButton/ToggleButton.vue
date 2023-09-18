<template>
    <label
        :class="classes"
        :disabled="disabled"
    >
        <input
            type="checkbox"
            class="sr-only"
            :disabled="disabled"
            :checked="checked"
            @change="onChange"
        >
        <!-- slot for an icon -->
        <slot name="button-icon" />
        <span v-if="label">{{ label }}</span>
        <!-- slot for an icon on the right -->
        <slot name="button-icon-right" />
    </label>
</template>
<script>
import "../Button/Button.css";
import "./ToggleButton.css";

export default {
    name: "EscrToggleButton",
    props: {
        /**
         * Whether or not the toggle is in the checked/true state
         */
        checked: {
            type: Boolean,
            required: true,
        },
        /**
         * Color of the button
         */
        color: {
            type: String,
            default: "primary",
            validator: function (value) {
                return [
                    "primary",
                    "secondary",
                    "tertiary",
                    "danger",
                    "text",
                ].indexOf(value) !== -1;
            },
        },
        /**
         * Text that appears as the button's label
         */
        label: {
            type: String,
            default: "",
        },
        /**
         * Function called when the user clicks on the toggle
         */
        onChange: {
            type: Function,
            required: true,
        },
        /**
         * Whether or not this button is disabled
         */
        disabled: {
            type: Boolean,
            default: false,
        },
        /**
         * Size of the button
         * @values small, large
         */
        size: {
            type: String,
            default: "large",
            validator: function (value) {
                return ["small", "large"].indexOf(value) !== -1;
            },
        },
    },
    computed: {
        classes() {
            return {
                "escr-toggle-button": true,
                "escr-toggle-button--disabled": this.disabled,
                [`escr-toggle-button--${this.color}`]: true,
                [`escr-toggle-button--active-${this.color}`]: this.checked,
                "escr-button": true,
                [`escr-button--${this.size}`]: true,
                "escr-button--icon-only": !this.label && (
                    this.$slots["button-icon"] || this.$slots["button-icon-right"]
                ),
            }
        }
    }
}
</script>
