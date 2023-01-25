import SegmentedButtonGroup from "../../vue/components/SegmentedButtonGroup/SegmentedButtonGroup.vue";

export default {
    title: "Components/Segmented Button",
    component: SegmentedButtonGroup,
    argTypes: {
        color: {
            control: { type: "select" },
            options: [
                "primary",
                "secondary",
            ],
        },
    },
};

const Template = (args, { argTypes }) => ({
    props: Object.keys(argTypes),
    components: { SegmentedButtonGroup },
    template: '<div style="width: 350px;"><SegmentedButtonGroup v-bind="$props" /></div>',
});


const buttons = [
    { label: "Regions", value: "regions", selected: true },
    { label: "Lines", value: "lines" },
    { label: "Text", value: "text" },
    { label: "Images", value: "images" },
];

export const Primary = Template.bind({});
Primary.args = {
    color: "primary",
    name: "storybook",
    options: buttons,
};

export const Secondary = Template.bind({});
Secondary.args = {
    color: "secondary",
    name: "storybook",
    options: buttons,
};
