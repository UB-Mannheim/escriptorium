import Button from "../../vue/components/Button/Button.vue";

export default {
    title: "Components/Button",
    component: Button,
    argTypes: {
        color: {
            control: { type: "select" },
            options: [
                "primary",
                "secondary",
                "tertiary",
                "danger",
                "outline-primary",
                "outline-secondary",
                "outline-tertiary",
                "outline-danger",
            ],
        },
        size: {
            control: { type: "select" },
            options: ["small", "large"],
        },
    },
};

const Template = (args, { argTypes }) => ({
    props: Object.keys(argTypes),
    components: { Button },
    template: '<Button v-bind="$props" />',
});

export const Primary = Template.bind({});
Primary.args = {
    label: "Button",
    onClick: () => {},
};

export const Secondary = Template.bind({});
Secondary.args = {
    label: "Button",
    onClick: () => {},
    color: "secondary",
};

export const Tertiary = Template.bind({});
Tertiary.args = {
    label: "Button",
    onClick: () => {},
    color: "tertiary",
};

export const Danger = Template.bind({});
Danger.args = {
    label: "Button",
    onClick: () => {},
    color: "danger",
};

export const OutlinePrimary = Template.bind({});
OutlinePrimary.args = {
    label: "Button",
    onClick: () => {},
    color: "outline-primary",
};

export const OutlineSecondary = Template.bind({});
OutlineSecondary.args = {
    label: "Button",
    onClick: () => {},
    color: "outline-secondary",
};

export const OutlineTertiary = Template.bind({});
OutlineTertiary.args = {
    label: "Button",
    onClick: () => {},
    color: "outline-tertiary",
};

export const OutlineDanger = Template.bind({});
OutlineDanger.args = {
    label: "Button",
    onClick: () => {},
    color: "outline-danger",
};

export const Small = Template.bind({});
Small.args = {
    label: "Button",
    onClick: () => {},
    color: "primary",
    size: "small",
};
export const SmallOutline = Template.bind({});
SmallOutline.args = {
    label: "Button",
    onClick: () => {},
    color: "outline-primary",
    size: "small",
};
