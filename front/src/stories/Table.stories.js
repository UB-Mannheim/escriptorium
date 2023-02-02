import Table from "../../vue/components/Table/Table.vue";

export default {
    title: "Components/Table",
    component: Table,
};

let items = [
    { id: 1, name: "Project Name", owner: "Ryuichi Sakamoto", updated: "2022-08-09" },
    { id: 2, name: "Second Project", owner: "Haruomi Hosono", updated: "2023-01-31" },
    { id: 3, name: "A Third Project", owner: "Yukihiro Takahashi", updated: "2022-01-09" },
];

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
    items,
    itemKey: "id"
};

const onSort = (field, direction) => {
    const alphabeticSort = (key) => (a, b) => {
        return a[key].toString().localeCompare(b[key].toString());
    };
    if (direction === 0) {
        items.sort(alphabeticSort("id"));
    } else {
        items.sort(alphabeticSort(field));
        if (direction === -1) {
            items.reverse();
        }
    }
}

export const SortableTable = Template.bind({});
SortableTable.args = {
    ...BasicTable.args,
    items,
    headers: BasicTable.args.headers.map((header) => ({ ...header, sortable: true })),
    onSort,
};

export const LinkableTable = Template.bind({});
LinkableTable.args = {
    ...BasicTable.args,
    items: items.map((item) => ({ ...item, href: window.parent.location })),
    linkable: true,
    onSort,
};
