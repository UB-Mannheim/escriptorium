import Button from "../../vue/components/Button/Button.vue";
import PlusIcon from "../../vue/components/Icons/PlusIcon/PlusIcon.vue";
import ImagesIcon from "../../vue/components/Icons/ImagesIcon/ImagesIcon.vue";

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
                "link-primary",
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
    template: "<Button v-bind=\"$props\" />",
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

export const Disabled = Template.bind({});
Disabled.args = {
    label: "Button",
    onClick: () => {},
    color: "primary",
    disabled: true,
};
export const DisabledOutline = Template.bind({});
DisabledOutline.args = {
    label: "Button",
    onClick: () => {},
    color: "outline-primary",
    disabled: true,
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

const IconTemplate = (args, { argTypes }) => ({
    props: Object.keys(argTypes),
    components: { Button, PlusIcon },
    template: `
        <Button v-bind="$props">
            <template v-slot:button-icon>
                <PlusIcon />
            </template>
        </Button>
    `,
});
export const PrimaryWithIcon = IconTemplate.bind({});
PrimaryWithIcon.args = {
    label: "Button",
    onClick: () => {},
    color: "primary",
};
export const OutlineWithIcon = IconTemplate.bind({});
OutlineWithIcon.args = {
    label: "Button",
    onClick: () => {},
    color: "outline-primary",
};
export const SmallWithIcon = IconTemplate.bind({});
SmallWithIcon.args = {
    label: "Button",
    onClick: () => {},
    color: "outline-danger",
    size: "small",
};
export const DisabledWithIcon = IconTemplate.bind({});
DisabledWithIcon.args = {
    label: "Button",
    onClick: () => {},
    color: "secondary",
    disabled: true,
};

const IconOnlyTemplate = (args, { argTypes }) => ({
    props: Object.keys(argTypes),
    components: { Button, ImagesIcon },
    template: `
        <Button v-bind="$props">
            <template v-slot:button-icon>
                <ImagesIcon />
            </template>
        </Button>
    `,
});
export const IconOnlyButton = IconOnlyTemplate.bind({});
IconOnlyButton.args = {
    onClick: () => {},
    color: "primary",
    size: "small",
};
