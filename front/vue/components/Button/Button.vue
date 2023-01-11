<template>
    <button type="button" :class="classes" @click="onClick">{{ label }}</button>
</template>

<script>
import './Button.css';

export default {
    name: 'escr-button',

    props: {
        /**
         * Color of the button
         */
        color: {
            type: String,
            default: 'primary',
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
                ].indexOf(value) !== -1;
            },
        },
        /**
         * Text that appears as the button's label
         */
        label: {
            type: String,
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
            default: 'large',
            validator: function (value) {
                return ['small', 'large'].indexOf(value) !== -1;
            },
        },
    },

    computed: {
        classes() {
            return {
                'escr-button': true,
                [`escr-button--${this.color}`]: true,
                [`escr-button--${this.size}`]: true,
                'escr-icon-button': !!this.icon,
            };
        },
    },

}

</script>
