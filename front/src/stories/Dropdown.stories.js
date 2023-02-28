import EscrDropdown from "../../vue/components/Dropdown/Dropdown.vue";
import "../../vue/components/Common/Card.css";

export default {
    title: "Components/Dropdown",
    component: EscrDropdown,
    argTypes: {
        onChange: { action: "changed" },
    },
};

const Template = (args, { argTypes }) => ({
    props: Object.keys(argTypes),
    components: { EscrDropdown },
    template: `
    <div class="escr-card escr-card-padding" style="width: 250px;">
        <EscrDropdown v-bind="$props" />
    </div>
    `,
});

const options = [
    {
        label: "Transcription Layer 1",
        value: 1,
    },
    {
        label: "second layer",
        value: 2,
    },
    {
        label: "Transcription layer with a very very very long name!",
        value: 3,
    },
];

export const Dropdown = Template.bind({});
Dropdown.args = { options };

const DarkTemplate = (args, { argTypes }) => ({
    props: Object.keys(argTypes),
    components: { EscrDropdown },
    template: `
        <div
            class="escr-card escr-card-padding"
            style="background: var(--background2); width: 350px;"
        >
            <EscrDropdown v-bind="$props" />
        </div>
    `,
});
export const LargerDropdownOnBG2 = DarkTemplate.bind({});
LargerDropdownOnBG2.args = { options };

export const DisabledDropdown = Template.bind({});
DisabledDropdown.args = {
    disabled: true,
    options,
};
