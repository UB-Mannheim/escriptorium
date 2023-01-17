import TagFilter from "../../vue/components/TagFilter/TagFilter.vue";

import { ManyTags } from "./Tags.stories";

export default {
    title: "Components/Tag Filter",
    component: TagFilter,
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
