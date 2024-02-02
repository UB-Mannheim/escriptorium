<template>
    <div
        :class="classes"
        role="group"
    >
        <div
            v-for="option in options"
            :key="option.value"
        >
            <input
                :id="`${name}-${option.value}`"
                type="radio"
                class="sr-only"
                :value="option.value"
                :name="name"
                :checked="option.selected"
                :disabled="disabled"
                @change="() => onChangeSelection(option.value)"
            >
            <VDropdown
                v-if="option.tooltip"
                theme="escr-tooltip-small"
                placement="bottom"
                :distance="8"
                :triggers="['hover']"
            >
                <label :for="`${name}-${option.value}`">
                    <component
                        :is="option.label"
                        v-if="typeof option.label !== 'string'"
                    />
                    <span v-else>
                        {{ option.label }}
                    </span>
                </label>
                <template #popper>
                    <span class="escr-tooltip-text">
                        {{ option.tooltip }}
                    </span>
                </template>
            </VDropdown>
            <label
                v-else
                :for="`${name}-${option.value}`"
            >
                <component
                    :is="option.label"
                    v-if="typeof option.label !== 'string'"
                />
                <span v-else>
                    {{ option.label }}
                </span>
            </label>
        </div>
    </div>
</template>

<script>
import { Dropdown as VDropdown } from "floating-vue";
import "./SegmentedButtonGroup.css";

export default {
    name: "EscrSegmentedButtonGroup",
    components: {
        VDropdown,
    },
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
    computed: {
        classes() {
            return {
                "escr-segmented-button-group": true,
                [`escr-segmented-button-group--${this.color}`]: true,
            };
        },
    },
};
</script>
