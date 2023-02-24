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
            pk: 0,
            variant: 1,
            color: "#e0726e",
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
            variant: 9,
            color: "#99aff2",
        },
        {
            pk: 2,
            name: "Third tag",
            variant: 5,
            color: "#f2cd5c",
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
            variant: 3,
            color: "#ff9a6f",
        },
        {
            pk: 4,
            name: "Fifth tag",
            variant: 6,
            color: "#cbe364",
        },
        {
            pk: 5,
            name: "Sixth tag",
            variant: 11,
            color: "#f2a7c3",
        },
        {
            pk: 6,
            name: "Long tag name 7",
            variant: 7,
            color: "#80c6ba",
        }
    ],
    wrap: false,
};

export const ManyTagsWrapped = Template.bind({});
ManyTagsWrapped.args = {
    tags: ManyTags.args.tags,
    wrap: true,
};
