import Tags from "../../vue/components/Tags/Tags.vue";
import { tagVariants } from "../../vue/store/util/color";

export default {
    title: "Components/Tags",
    component: Tags,
    argTypes: {
        wrap: {
            control: "boolean",
        },
    },
};

const Template = (args, { argTypes }) => ({
    props: Object.keys(argTypes),
    components: { Tags },
    template: `
        <div style="width: 350px;">
            <Tags v-bind="$props" />
        </div>
    `,
});

export const SingleTag = Template.bind({});
SingleTag.args = {
    tags: [
        {
            pk: 0,
            variant: 1,
            color: tagVariants[1],
            name: "Tag Name",
        },
    ],
};
export const MultipleTags = Template.bind({});
MultipleTags.args = {
    tags: [
        ...SingleTag.args.tags,
        {
            pk: 1,
            name: "Longer tag name",
            variant: 12,
            color: tagVariants[12],
        },
        {
            pk: 2,
            name: "Third tag",
            variant: 8,
            color: tagVariants[8],
        },
    ],
};

export const ManyTags = Template.bind({});
ManyTags.args = {
    tags: [
        ...MultipleTags.args.tags,
        {
            pk: 3,
            name: "Fourth tag",
            variant: 28,
            color: tagVariants[28],
        },
        {
            pk: 4,
            name: "Fifth tag",
            variant: 22,
            color: tagVariants[22],
        },
        {
            pk: 5,
            name: "Sixth tag",
            variant: 11,
            color: tagVariants[11],
        },
        {
            pk: 6,
            name: "Long tag name 7",
            variant: 15,
            color: tagVariants[15],
        },
    ],
    wrap: false,
};

export const ManyTagsWrapped = Template.bind({});
ManyTagsWrapped.args = {
    tags: ManyTags.args.tags,
    wrap: true,
};
