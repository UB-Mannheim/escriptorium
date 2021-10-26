<template>
    <div class="escr-characters-card escr-card escr-card-padding">
        <div class="escr-card-header">
            <h2>{{ label }}</h2>
            <div class="escr-card-actions">
                <EscrButton
                    label="View"
                    size="small"
                    :disabled="loading"
                    :on-click="onView"
                >
                    <template #button-icon>
                        <OpenIcon />
                    </template>
                </EscrButton>
            </div>
        </div>
        <SegmentedButtonGroup
            color="secondary"
            name="characters-sort"
            :disabled="loading"
            :options="sortOptions"
            :on-change-selection="onSortCharacters"
        />
        <dl
            v-if="items.length"
        >
            <div
                v-for="item in items"
                :key="item.char"
                v-tooltip.bottom="unicodeCodePoint(item.char)"
            >
                <dt :class="item.char === ' ' ? 'space-char' : ''">
                    {{ item.char }}
                </dt>
                <dd>{{ item.frequency }}</dd>
            </div>
        </dl>
    </div>
</template>
<script>
import EscrButton from "../Button/Button.vue";
import OpenIcon from "../Icons/OpenIcon/OpenIcon.vue";
import SegmentedButtonGroup from "../SegmentedButtonGroup/SegmentedButtonGroup.vue";
import "./CharactersCard.css";

export default {
    name: "EscrCharactersCard",
    components: { EscrButton, OpenIcon, SegmentedButtonGroup },
    props: {
        /**
         * A list of character items, each of which should have a `char` and `frequency` field.
         */
        items: {
            type: Array,
            default: () => [],
        },
        /**
         * The label for the card.
         */
        label: {
            type: String,
            default: "Characters",
        },
        /**
         * Boolean indicating whether or not data is loading.
         */
        loading: {
            type: Boolean,
            default: false,
        },
        /**
         * Callback function for switching the sort option.
         */
        onSortCharacters: {
            type: Function,
            required: true,
        },
        /**
         * Callback function for opening the "View" modal.
         */
        onView: {
            type: Function,
            required: true,
        },
        /**
         * The currently selected sort option.
         */
        sort: {
            type: String,
            default: "char",
            validator(value) {
                return ["char", "frequency"].includes(value);
            },
        },
    },
    computed: {
        /**
         * Mapping of sort options to label/value pairs, passing the `selected` prop to the
         * currently selected one.
         */
        sortOptions() {
            return [
                { label: "by Character", value: "char" },
                { label: "by Frequency", value: "frequency" },
            ].map((sort) => ({
                ...sort,
                selected: this.sort === sort.value,
            }));
        },
    },
    methods: {
        /**
         * Convert a character into a string representation of its Unicode code point,
         * represented in hexadecimal, with U+ at the beginning, such as U+2ACC.
         */
        unicodeCodePoint(str) {
            return `U+${str.codePointAt(0).toString(16).toUpperCase()}`;
        },
    }
}
</script>