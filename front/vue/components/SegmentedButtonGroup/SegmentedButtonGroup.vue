<script>
import "./SegmentedButtonGroup.css";

export default {
    name: "EscrSegmentedButtonGroup",
    functional: true,
    props: {
        /**
         * Color of the selected button
         * @values primary, secondary
         */
        color: {
            type: String,
            default: "primary",
            validator: function(value) {
                return ["primary", "secondary"].indexOf(value) !== -1;
            },
        },
        /**
         * Boolean indicating whether or not this entire component should be disabled, for example,
         * during data loading.
         */
        disabled: {
            type: Boolean,
            default: false,
        },
        /**
         * List of options, each of which should have a `value` and a `label`.
         * Optionally, one may have a `selected` boolean.
         */
        options: {
            type: Array,
            required: true,
            validator: function(opts) {
                return (
                    Array.isArray(opts) &&
                    opts.length > 0 &&
                    Object.hasOwn(opts[0], "value")
                );
            },
        },
        /**
         * The name attribute of the radio input group
         */
        name: {
            type: String,
            required: true,
        },
        /**
         * Function that executes when the selection is changed. Should accept
         * a string (with the option's `value`) as the sole parameter.
         */
        onChangeSelection: {
            type: Function,
            required: true,
        },
    },
    render: (h, context) => {
        /**
         * Reusable function to render a single option's radio input and label
         */
        function renderOption(option) {
            return [
                h(
                    "input",
                    {
                        domProps: {
                            type: "radio",
                            id: `${context.props.name}-${option.value}`,
                            value: option.value,
                            name: context.props.name,
                            checked: option.selected,
                            disabled: context.props.disabled,
                        },
                        class: {"sr-only": true },
                        on: {
                            change: () => context.props.onChangeSelection(option.value),
                        },
                    },
                ),
                h(
                    "label",
                    {
                        domProps: {
                            htmlFor: `${context.props.name}-${option.value}`,
                        },
                    },
                    option.label,
                ),
            ]
        }
        /**
         * Render the container div and radio children
         */
        return h(
            "div",
            {
                class: {
                    "escr-segmented-button-group": true,
                    [`escr-segmented-button-group--${context.props.color}`]: true,
                },
                domProps: {
                    role: "group",
                }
            },
            context.props.options.map((option) => renderOption(option)),
        );
    },
};
</script>
