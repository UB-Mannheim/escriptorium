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
            variant: 1,
            name: "Tag Name",
        },
    ],
};
export const MultipleTags = Template.bind({});
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

export const ManyTags = Template.bind({});
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

export const ManyTagsWrapped = Template.bind({});
ManyTagsWrapped.args = {
    tags: ManyTags.args.tags,
    wrap: true,
};
