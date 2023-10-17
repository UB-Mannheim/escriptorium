<template>
    <div class="escr-dropdown">
        <select
            :aria-label="label"
            :disabled="disabled"
            :invalid="!options || !options.some((option) => option.selected)"
            @change="onChange"
        >
            <option
                value=""
                disabled
                :selected="!options || !options.some((option) => option.selected)"
            >
                Select
            </option>
            <option
                v-for="option in options"
                :key="option.value"
                :value="option.value"
                :selected="option.selected"
            >
                {{ option.label }}
            </option>
        </select>
        <ChevronDownIcon />
    </div>
</template>
<script>
import ChevronDownIcon from "../Icons/ChevronDownIcon/ChevronDownIcon.vue";
import "./Dropdown.css";

export default {
    name: "EscrDropdown",
    components: { ChevronDownIcon },
    props: {
        /**
         * Boolean indicating if the dropdown should be disabled.
         */
        disabled: {
            type: Boolean,
            default: false,
        },
        /**
         * Optional label, only used as an aria-label for accessibility.
         */
        label: {
            type: String,
            default: "",
        },
        /**
         * List of options, each of which should be an object:
         * {
         *     value: String,
         *     label: String,
         *     selected: Boolean,
         * }
         */
        options: {
            type: Array,
            required: true,
        },
        /**
         * Callback for changing the selected option.
         */
        onChange: {
            type: Function,
            required: true,
        },
    },
}
</script>
