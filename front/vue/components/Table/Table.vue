<template>
    <table class="escr-table">
        <thead>
            <tr>
                <th
                    v-for="header in headers"
                    :key="header.value"
                >
                    <div>
                        <span v-if="!header.sortable">
                            {{ header.label }}
                        </span>
                        <button
                            v-else
                            class="escr-sort-button"
                            @click="() => setSort(header)"
                        >
                            <span>
                                {{ header.label }}
                            </span>
                            <SortIcon
                                :state="
                                    sortState.value === header.value
                                        ? sortState.direction
                                        : 0
                                "
                            />
                        </button>
                    </div>
                </th>
            </tr>
        </thead>
        <tbody>
            <tr
                v-for="item in items"
                :key="item[itemKey]"
            >
                <td
                    v-for="(header, index) in headers"
                    :key="header.value"
                >
                    <a
                        v-if="linkable && item.href && index == 0"
                        class="row-link"
                        :href="item.href"
                    >
                        <component
                            :is="header.component"
                            v-if="header.component && item[header.value]"
                            class="sr-only"
                            v-bind="item[header.value]"
                        />
                        <span
                            v-else
                            class="sr-only"
                        >
                            {{ item[header.value] }}
                        </span>
                    </a>
                    <component
                        :is="header.component"
                        v-if="header.component && item[header.value]"
                        v-bind="item[header.value]"
                    />
                    <span v-else>
                        {{ item[header.value] }}
                    </span>
                </td>
                <td
                    v-if="!!$scopedSlots['actions']"
                    class="escr-row-actions"
                >
                    <div>
                        <slot
                            name="actions"
                            :item="item"
                        />
                    </div>
                </td>
            </tr>
        </tbody>
    </table>
</template>
<script>
import SortIcon from "../Icons/SortIcon/SortIcon.vue";
import "./Table.css";

export default {
    name: "EscrTable",
    components: {
        SortIcon,
    },
    props: {
        /**
         * List of headers, each of which is an object that should have a `value` and a `label`.
         * To make a column sortable, set the `sortable` boolean for its header to `true`.
         *
         * When using sortable columns, data may be sorted by using the callback function prop
         * `onSort` to mutate the `items` prop.
         *
         * It is also possible to use a Vue component for table cells. To do this, add a `component`
         * key to the header for that column and pass the component along. In the data, the item's
         * value for that header name must be an object containing the props for that component.
         */
        headers: {
            type: Array,
            required: true,
            validator(value) {
                return value.every((header) => Object.prototype.hasOwnProperty.call(header, "value")
                && Object.prototype.hasOwnProperty.call(header, "label"));
            },
        },
        /**
         * A unique property on each item that will be used as its key.
         */
        itemKey: {
            type: String,
            required: true,
        },
        /**
         * List of items that should appear in the table. Each item should be an object with
         * keys corresponding to each header's `value` in `headers`, as well as a unique value for
         * the `itemKey`.
         *
         * If any item has a `href` property and the `linkable` prop is set to `true`, that item's
         * row will also be clickable to navigate to that URL.
         */
        items: {
            type: Array,
            required: true,
        },
        /**
         * Boolean indicating whether or not an item's row should link to its `href` value.
         */
        linkable: {
            type: Boolean,
            default: false,
        },
        /**
         * A callback function for sorting, which may be used for frontend sorting or for API calls
         * to retrieve sorted data from a backend, and which should mutate the `items` prop.
         *
         * Must be a function that accepts a single object param with the following two keys:
         * `field`, a string for the field to sort on, and
         * `direction`, which will be one of the numbers 0, -1, or 1.
         */
        onSort: {
            type: Function,
            // eslint-disable-next-line no-unused-vars
            default: ({ field, direction }) => {},
        },
    },
    data() {
        return {
            sortState: {
                direction: 0,
            },
        };
    },
    methods: {
        /**
         * When a header is clicked to change the sort state, update the sort state
         * accordingly and call the `onSort` callback prop.
         */
        setSort(header) {
            const { value, direction } = this.sortState;
            let newDirection = 1;
            if (value === header.value && direction !== 0) {
                newDirection = direction === 1 ? -1 : 0;
            }
            this.sortState = {
                value: header.value,
                direction: newDirection,
                sortFn: this.sortState.sortFn || undefined,
            };
            this.onSort({ field: header.value, direction: newDirection });
        },
    },
}
</script>
