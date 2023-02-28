<template>
    <div class="escr-dropdown">
        <select
            :disabled="disabled"
            @change="onChange"
        >
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
        disabled: {
            type: Boolean,
            default: false,
        },
        options: {
            type: Array,
            required: true,
        },
        onChange: {
            type: Function,
            required: true,
        },
    },
}
</script>
