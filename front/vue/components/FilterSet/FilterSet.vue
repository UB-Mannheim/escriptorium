<template>
    <div class="escr-filter-set">
        <span>Filter by:</span>
        <FilterButton
            :active="tagFilterActive"
            :count="tagCount"
            label="Tags"
            :on-click="() => toggleOpen('tags')"
            :on-clear="() => clearFilter('tags')"
        >
            <template #filter-icon="{active}">
                <TagIcon :active="active" />
            </template>
        </FilterButton>
        <TagFilter
            v-if="openFilter === 'tags'"
            :tags="tags"
            :selected="tagFilterSelectedTags"
            :operator="tagFilterOperator"
            :without-tag-selected="withoutTagSelected"
            :on-apply="toggleClosedAndFilter"
            :on-cancel="() => toggleOpen(undefined)"
        />
    </div>
</template>
<script>
import { mapActions, mapGetters, mapState } from "vuex";
import FilterButton from "../FilterButton/FilterButton.vue";
import TagFilter from "../TagFilter/TagFilter.vue";
import TagIcon from "../Icons/TagIcon/TagIcon.vue";
import "./FilterSet.css";

export default {
    name: "EscrFilterSet",
    components: { TagFilter, TagIcon, FilterButton },
    props: {
        /**
         * List of all tags on all [documents/projects/images] in view.
         * TODO: Get this from the store instead.
         */
        tags: {
            type: Array,
            default: () => []
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
            "withoutTagSelected",
        ]),
    },
    methods: {
        /**
         * Result of clicking the "clear" button by a filter
         */
        clearFilter(type) {
            this.openFilter = undefined;
            this.removeFilter(type);
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
        toggleClosedAndFilter(value) {
            this.openFilter = undefined;
            this.addFilter({ type: "tags", value });
        },
        ...mapActions("filter", [
            "addFilter",
            "removeFilter",
        ]),
    },
};
</script>
