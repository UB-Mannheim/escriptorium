import ToggleButtonGroup from "../../vue/components/ToggleButtonGroup/ToggleButtonGroup.vue";

export default {
    title: "Components/Toggle Button",
    component: ToggleButtonGroup,
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
    components: { ToggleButtonGroup },
    template: '<ToggleButtonGroup v-bind="$props" />',
});


const buttons = [
    { label: "Regions", value: "regions" },
    { label: "Lines", value: "lines" },
    { label: "Text", value: "text" },
    { label: "Images", value: "images" },
];

export const Primary = Template.bind({});
Primary.args = {
    color: "primary",
    options: buttons,
};

export const Secondary = Template.bind({});
Secondary.args = {
    color: "secondary",
    options: buttons,
};
