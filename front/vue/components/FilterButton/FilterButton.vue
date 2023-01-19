<template>
    <div :class="classes">
        <button class="escr-button" @click="onClick">
            <slot name="filter-icon" :active="active"></slot>
            <span class="label">{{ label }}</span>
            <span v-if="active && count" class="count">{{ count }}</span>
        </button>
        <button class="escr-clear-filter-button" v-if="active" @click="onClear">
            <XIcon />
            <span class="sr-only">Clear filter</span>
        </button>
    </div>
</template>
<script>

import "../Button/Button.css";
import XIcon from "../Icons/XIcon/XIcon.vue";
import "./FilterButton.css";

export default {
    name: "escr-filter-button",
    props: {
        active: {
            type: Boolean,
        },
        count: {
            type: Number,
        },
        label: {
            type: String,
        },
        onClear: {
            type: Function,
        },
        onClick: {
            type: Function,
        },
    },
    computed: {
        classes() {
            return {
                "escr-filter-button": true,
                "escr-filter-button--active": this.active,
            };
        }
    },
    components: { XIcon }
}

</script>
