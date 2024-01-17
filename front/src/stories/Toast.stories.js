import Vue from "vue";
import EscrButton from "../../vue/components/Button/Button.vue";
import EscrToast from "../../vue/components/Toast/Toast.vue";
import EscrToastGroup from "../../vue/components/Toast/ToastGroup.vue";

const colors = ["alert", "success", "text"];
const messages = [
    "This is an example message.",
    "Test",
    "Random alert message",
    "Rather long-ish alert message example for display purposes",
];

export default {
    title: "Components/Toast",
    component: EscrToast,
    argTypes: {
        color: {
            control: { type: "select" },
            options: colors,
        },
    },
};

const Template = (args, { argTypes }) => ({
    props: Object.keys(argTypes),
    components: { EscrToast },
    template: '<EscrToast v-bind="$props" />',
});

export const Toast = Template.bind({});
Toast.args = {
    message: messages[0],
};
export const ToastWithActionLink = Template.bind({});
ToastWithActionLink.args = {
    message: messages[0],
    actionLink: window.parent.location,
    actionLabel: "Click me",
};

export const ToastWithActionFunction = Template.bind({});
ToastWithActionFunction.args = {
    message: messages[0],
    actionLabel: "Click me",
    actionFn: () => {},
};

const GroupTemplate = (args, { argTypes }) => ({
    props: Object.keys(argTypes),
    components: { EscrToastGroup, EscrButton },
    template: `
        <div>
            <EscrButton
                :on-click="$props.onClick"
                label="Create toast alert"
            />
            <EscrToastGroup />
        </div>
    `,
});
export const ToastGroup = GroupTemplate.bind({});
ToastGroup.args = {
    onClick: () => {
        Vue.prototype.$store.dispatch("alerts/add", {
            color: colors[Math.floor(Math.random() * colors.length)],
            message: messages[Math.floor(Math.random() * messages.length)],
        });
    },
};
