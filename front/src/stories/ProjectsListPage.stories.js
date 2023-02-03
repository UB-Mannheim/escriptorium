import EscrNewProjectModal from "../../vue/pages/ProjectsList/NewProjectModal.vue";

export default {
    title: "Pages/ProjectsList",
    component: EscrNewProjectModal,
    argTypes: {
        onClick: { action: "clicked" },
        onInput: { action: "input" },
        onCancel: { action: "cancel" },
    },
};

const Template = (args, { argTypes }) => ({
    props: Object.keys(argTypes),
    components: { EscrNewProjectModal },
    template: "<EscrNewProjectModal v-bind=\"$props\" />",
});
export const NewProjectModal = Template.bind({});
