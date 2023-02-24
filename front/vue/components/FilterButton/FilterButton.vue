<template>
    <div :class="classes">
        <button class="escr-button" @click="onClick">
            <!-- slot for an icon, if you want one in the filter button label -->
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

import XIcon from "../Icons/XIcon/XIcon.vue";
import "../Button/Button.css";
import "./FilterButton.css";

export default {
    name: "escr-filter-button",
    props: {
        /**
         * Whether or not the filter is currently applied and filtering data
         */
        active: {
            type: Boolean,
        },
        /**
         * Number to display for filters with a visible count (such as tags)
         */
        count: {
            type: Number,
        },
        /**
         * Label for the filter button
         */
        label: {
            type: String,
            required: true,
        },
        /**
         * Callback for clearing the filter with the "X" button
         */
        onClear: {
            type: Function,
            required: true,
        },
        /**
         * Click event handler (should open the filter's modal/dialog)
         */
        onClick: {
            type: Function,
            required: true,
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
