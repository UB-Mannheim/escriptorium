import TagFilterComponent from "../../vue/components/TagFilter/TagFilter.vue";

import { ManyTags } from "./Tags.stories";

export default {
    title: "Components/Tag Filter",
    component: TagFilterComponent,
};

const Template = (args, { argTypes }) => ({
    props: Object.keys(argTypes),
    components: { TagFilterComponent },
    template: `
        <TagFilterComponent v-bind="$props" />
    `,
});
export const TagFilter = Template.bind({});
TagFilter.args = {
    tags: ManyTags.args.tags,
};
