import Button from "../../vue/components/Button/Button.vue";
import Table from "../../vue/components/Table/Table.vue";
import TrashIcon from "../../vue/components/Icons/TrashIcon/TrashIcon.vue";
import { onSort } from "./util";

export default {
    title: "Components/Table",
    component: Table,
};

let items = [
    {
        pk: 1,
        name: "Project Name",
        owner: "Ryuichi Sakamoto",
        updated: "2022-08-09",
    },
    {
        pk: 2,
        name: "Second Project",
        owner: "Haruomi Hosono",
        updated: "2023-01-31",
    },
    {
        pk: 3,
        name: "A Third Project",
        owner: "Yukihiro Takahashi",
        updated: "2022-01-09",
    },
];

const Template = (args, { argTypes }) => ({
    props: Object.keys(argTypes),
    components: { Table },
    template: '<Table v-bind="$props" />',
});
export const BasicTable = Template.bind({});
BasicTable.args = {
    headers: [
        { label: "Name", value: "name" },
        { label: "Owner", value: "owner" },
        { label: "Last updated", value: "updated" },
    ],
    items,
    itemKey: "id",
};

export const SortableTable = Template.bind({});
SortableTable.args = {
    ...BasicTable.args,
    items,
    headers: BasicTable.args.headers.map((header) => ({
        ...header,
        sortable: true,
    })),
    onSort,
};

export const LinkableTable = Template.bind({});
LinkableTable.args = {
    ...BasicTable.args,
    items: items.map((item) => ({ ...item, href: window.parent.location })),
    linkable: true,
    onSort,
};

const ActionsTemplate = (args, { argTypes }) => ({
    props: Object.keys(argTypes),
    components: { Button, Table, TrashIcon },
    template: `
        <Table v-bind="$props">
            <template #actions>
                <Button
                    size="small"
                    color="text"
                    :onClick="() => {}"
                >
                    <template #button-icon>
                        <TrashIcon />
                    </template>
                </Button>
            </template>
        </Table>
    `,
});
export const TableWithActions = ActionsTemplate.bind({});
TableWithActions.args = {
    ...BasicTable.args,
};
