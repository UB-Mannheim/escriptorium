import TagFilter from "../../vue/components/TagFilter/TagFilter.vue";
import FilterButton from "../../vue/components/FilterButton/FilterButton.vue";
import TagIcon from "../../vue/components/Icons/TagIcon/TagIcon.vue";
import FilterSet from "../../vue/components/FilterSet/FilterSet.vue";
import "../../vue/components/Common/Card.css";

import { ManyTags } from "./Tags.stories";

export default {
    title: "Components/Tag Filter",
    component: TagFilter,
    subcomponents: { FilterButton, TagIcon },
    argTypes: {
        onClick: { action: "clicked" },
        onClear: { action: "cleared" },
    },
};

const Template = (args, { argTypes }) => ({
    props: Object.keys(argTypes),
    components: { TagFilter },
    template: `
        <TagFilter v-bind="$props" />
    `,
});
export const TagFilterModal = Template.bind({});
TagFilterModal.args = {
    tags: ManyTags.args.tags,
    selected: ["Third tag", "Fifth tag"],
};

const ButtonTemplate = (args, { argTypes }) => ({
    props: Object.keys(argTypes),
    components: { FilterButton, TagIcon },
    template: `
        <div style="width: 110px;" class="escr-card escr-card-padding">
            <FilterButton v-bind="$props">
                <template v-slot:filter-icon="{active}">
                    <TagIcon :active="active" />
                </template>
            </FilterButton>
        </div>
    `,
});
export const TagFilterButton = ButtonTemplate.bind({});
TagFilterButton.args = {
    active: true,
    count: 2,
    label: "Tags",
};

const FilterSetTemplate = (args, { argTypes }) => ({
    props: Object.keys(argTypes),
    components: { FilterSet },
    template: `
        <div class="escr-card escr-card-padding">
            <FilterSet v-bind="$props" />
        </div>
    `,
});
export const TagFilterWithButton = FilterSetTemplate.bind({});
TagFilterWithButton.args = {
    tags: ManyTags.args.tags,
};
