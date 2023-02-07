import TextField from "../../vue/components/TextField/TextField.vue";
import "../../vue/components/Common/Card.css";

export default {
    title: "Components/Forms",
    component: TextField,
};
const Template = (args, { argTypes }) => ({
    props: Object.keys(argTypes),
    components: { TextField },
    template: `
        <div style="width: 350px;" class="escr-card escr-card-padding">
            <TextField v-bind="$props" />
        </div>
    `,
});

export const SingleTextField = Template.bind({});
SingleTextField.args = {
    label: "Field label",
    placeholder: "Type here...",
};
