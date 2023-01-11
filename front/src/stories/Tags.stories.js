import Tags from "../../vue/components/Tags/Tags.vue";

export default {
    title: "Components/Tags",
    component: Tags,
    argTypes: {
        wrap: {
            control: "boolean",
        },
    },
};

const GroupTemplate = (args, { argTypes }) => ({
    props: Object.keys(argTypes),
    components: { Tags },
    template: `
        <div style="width: 350px;">
            <Tags v-bind="$props" />
        </div>
    `,
});

export const SingleTag = GroupTemplate.bind({});
SingleTag.args = {
    tags: [
        {
            variant: 1,
            name: "Tag Name",
        },
    ],
};
export const MultipleTags = GroupTemplate.bind({});
MultipleTags.args = {
    tags: [
        ...SingleTag.args.tags,
        {
            name: "Longer tag name",
            variant: 9,
        },
        {
            name: "Third tag",
            variant: 5,
        },
    ],
};

export const ManyTags = GroupTemplate.bind({});
ManyTags.args = {
    tags: [
        ...MultipleTags.args.tags,
        {
            name: "Fourth tag",
            variant: 3,
        },
        {
            name: "Fifth tag",
            variant: 6,
        },
        {
            name: "Sixth tag",
            variant: 11,
        },
        {
            name: "Long tag name 7",
            variant: 7,
        }
    ],
    wrap: false,
};

export const ManyTagsWrapped = GroupTemplate.bind({});
ManyTagsWrapped.args = {
    tags: ManyTags.args.tags,
    wrap: true,
};
