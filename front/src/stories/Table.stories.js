import Table from "../../vue/components/Table/Table.vue";

export default {
    title: "Components/Table",
    component: Table,
};


const Template = (args, { argTypes }) => ({
    props: Object.keys(argTypes),
    components: { Table },
    template: "<Table v-bind=\"$props\" />",
});
export const BasicTable = Template.bind({});
BasicTable.args = {
    headers: [
        { label: "Name", value: "name" },
        { label: "Owner", value: "owner" },
        { label: "Last updated", value: "updated" },
    ],
    items: [
        { id: 1, name: "Project Name", owner: "Ryuichi Sakamoto", updated: "2022-08-09" },
        { id: 2, name: "Second Project", owner: "Haruomi Hosono", updated: "2023-01-31" },
        { id: 3, name: "A Third Project", owner: "Yukihiro Takahashi", updated: "2022-01-09" },
    ],
    itemKey: "id"
};

export const SortableTable = Template.bind({});
SortableTable.args = {
    ...BasicTable.args,
    headers: BasicTable.args.headers.map((header) => ({ ...header, sortable: true })),
};

export const LinkableTable = Template.bind({});
LinkableTable.args = {
    ...SortableTable.args,
    items: SortableTable.args.items.map((item) => ({ ...item, href: window.parent.location })),
    linkable: true,
};
