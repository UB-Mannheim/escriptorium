<template>
    <button
        type="button"
        :class="classes"
        :disabled="disabled"
        @click="onClick"
    >
        <!-- slot for an icon -->
        <slot name="button-icon" />
        <span v-if="label">{{ label }}</span>
    </button>
</template>

<script>
import "./Button.css";

export default {
    name: "EscrButton",

    props: {
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
                    "outline-primary",
                    "outline-secondary",
                    "outline-tertiary",
                    "outline-danger",
                    "link-primary",
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
         * Function called when the user clicks on the button
         */
        onClick: {
            type: Function,
            required: true,
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
        /**
         * Whether or not this button is disabled
         */
        disabled: {
            type: Boolean,
            default: false,
        }
    },

    computed: {
        classes() {
            return {
                "escr-button": true,
                [`escr-button--${this.color}`]: true,
                [`escr-button--${this.size}`]: true,
            };
        },
    },

}

</script>
