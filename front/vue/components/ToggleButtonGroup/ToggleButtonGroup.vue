<template>
    <div role="group" :class="classes">
        <button
            v-for="option in options"
            type="button"
            :class="optionClasses(option)"
            :value="option.value"
            @click="onClick"
        >
            {{ option.label }}
        </button>
    </div>
</template>

<script>
import '../Button/Button.css';
import './ToggleButtonGroup.css';

export default {
    name: 'escr-toggle-button-group',
    props: {
        /**
         * Color of the selected button
         * @values primary, secondary
         */
        color: {
            type: String,
            default: 'primary',
            validator: function (value) {
                return [
                    'primary',
                    'secondary',
                ].indexOf(value) !== -1;
            },
        },
        /**
         * List of options, each of which should have a value and a label
         */
        options: {
            type: Array,
            required: true,
            validator: function (opts) {
                return Array.isArray(opts) && opts.length > 0 && Object.hasOwn(opts[0], 'value')
            }
        },
    },
    data: function () {
        return {
            selectedOption: Array.isArray(this.options) && this.options.length > 0
                ? this.options[0].value
                : '',
        }
    },
    computed: {
        classes() {
            return {
                'escr-toggle-button-group': true,
                [`escr-toggle-button-group--${this.color}`]: true,
                [`escr-toggle-button-group--${this.size}`]: true,
            };
        },
    },
    methods: {
        onClick: function (e) {
            this.selectedOption = e.target.value;
        },
        optionClasses: function (option) {
            return {
                'escr-button': true,
                'escr-button--large': true,
                'escr-button--active': option.value === this.selectedOption,
            };
        },
    },
    render: (h) => {
        return h('div', this.$slots.default)
    },
}

</script>
