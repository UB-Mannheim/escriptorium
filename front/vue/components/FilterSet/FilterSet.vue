<template>
    <div class="escr-filter-set">
        <span>Filter by:</span>
        <VMenu
            :delay="{ show: 0, hide: 100 }"
            :triggers="[]"
            :shown="openFilter === 'tags'"
            :auto-hide="false"
            @apply-hide="() => toggleOpen(undefined)"
        >
            <FilterButton
                :active="tagFilterActive"
                :count="tagCount"
                label="Tags"
                :on-click="() => toggleOpen('tags')"
                :on-clear="() => clearFilter('tags')"
                :disabled="disabled"
            >
                <template #filter-icon="{active}">
                    <TagIcon :active="active" />
                </template>
            </FilterButton>
            <template #popper>
                <TagFilter
                    v-if="openFilter === 'tags'"
                    :tags="tags"
                    :selected="tagFilterSelectedTags"
                    :operator="tagFilterOperator"
                    :untagged-selected="untaggedSelected"
                    :on-apply="toggleClosedAndFilter"
                    :on-cancel="() => toggleOpen(undefined)"
                />
            </template>
        </VMenu>
    </div>
</template>
<script>
import { Menu as VMenu } from "floating-vue";
import { mapActions, mapGetters, mapState } from "vuex";
import FilterButton from "../FilterButton/FilterButton.vue";
import TagFilter from "../TagFilter/TagFilter.vue";
import TagIcon from "../Icons/TagIcon/TagIcon.vue";
import "./FilterSet.css";

export default {
    name: "EscrFilterSet",
    components: { TagFilter, TagIcon, FilterButton, VMenu },
    props: {
        /**
         * Boolean indicating if the filter buttons should be disabled, e.g. during loading.
         */
        disabled: {
            type: Boolean,
            default: false,
        },
        /**
         * List of all tags on all [documents/projects/images] in view.
         */
        tags: {
            type: Array,
            default: () => [],
        },
        /**
         * Optional callback function to be performed after filter state changes.
         */
        onFilter: {
            type: Function,
            default: () => {},
        },
    },
    data() {
        return {
            openFilter: undefined,
        };
    },
    computed: {
        ...mapState({
            filters: (state) => state.filter.filters,
        }),
        ...mapGetters("filter", [
            "tagFilterActive",
            "tagCount",
            "tagFilter",
            "tagFilterOperator",
            "tagFilterSelectedTags",
            "untaggedSelected",
        ]),
    },
    methods: {
        /**
         * Result of clicking the "clear" button by a filter
         */
        clearFilter(type) {
            this.openFilter = undefined;
            this.removeFilter(type);
            this.onFilter();
        },
        /**
         * Result of clicking on a filter button (open/close filter dialog)
         */
        toggleOpen(type) {
            if (this.openFilter === type) {
                this.openFilter = undefined;
            } else {
                this.openFilter = type;
            }
        },
        /**
         * Result of clicking "Submit" on a filter dialog: close the dialog
         * and apply the filter
         */
        toggleClosedAndFilter({ operator, tags, untagged }) {
            this.openFilter = undefined;
            this.addFilter({
                type: "tags",
                value: untagged
                    ? Array.from(new Set([...tags, "none"]))
                    : tags.filter((t) => t !== "none"),
                operator,
            });
            this.onFilter();
        },
        ...mapActions("filter", [
            "addFilter",
            "removeFilter",
        ]),
    },
};
</script>
