import TagFilter from "../../vue/components/TagFilter/TagFilter.vue";
import FilterButton from "../../vue/components/FilterButton/FilterButton.vue";
import TagIcon from "../../vue/components/Icons/TagIcon/TagIcon.vue";

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

const WithButtonTemplate = (args, { argTypes }) => ({
    props: Object.keys(argTypes),
    components: { FilterButton, TagIcon },
    template: `
        <FilterButton v-bind="$props">
            <template v-slot:filter-icon="{active}">
                <TagIcon :active="active" />
            </template>
        </FilterButton>
    `,
});
export const TagFilterButton = WithButtonTemplate.bind({});
TagFilterButton.args = {
    active: true,
    count: 2,
    label: "Tags",
};
