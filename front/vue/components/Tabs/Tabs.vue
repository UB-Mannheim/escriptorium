<template>
    <div
        class="escr-tabs"
        role="tablist"
    >
        <button
            v-for="tab in tabs"
            :id="`tab-${tab.value}`"
            :key="tab.value"
            role="tab"
            class="escr-tab-btn"
            :class="{ active: value === tab.value }"
            :aria-selected="value === tab.value"
            :aria-controls="`panel-${tab.value}`"
            :tabindex="value === tab.value ? '0' : '-1'"
            @click="$emit('input', tab.value)"
        >
            {{ tab.label }}
            <span
                v-if="tab.badge && tab.badge > 0"
                class="badge"
            >
                {{ tab.badge }}
            </span>
        </button>
    </div>
</template>

<script>
import "./Tabs.css";

export default {
    name: "EscrTabs",
    props: {
        /**
         * The currently active tab value
         */
        value: {
            type: String,
            required: true,
        },
        /**
         * List of tab options, each of which should be an object:
         * {
         *     value: String,
         *     label: String,
         *     badge?: Number
         * }
         */
        tabs: {
            type: Array,
            required: true,
        },
    },
};
</script>
