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
                v-for="item in sortedItems"
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
                        <span class="sr-only">{{ item[header.value] }}</span>
                    </a>
                    <span>
                        {{ item[header.value] }}
                    </span>
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
         * Data may be sorted on the frontend (default), or using the callback function prop
         * `onSort` to make API calls and mutate the `items` prop. (If you use `onSort`, you must
         * also set the boolean prop `useOnSort` to `true`.)
         *
         * For frontend sorting, to define a non-alphabetic sorting algorithm for a column,
         * include a `sortFn` function. `sortFn` should be a curried function that accepts
         * a string key as the parameter for the outer function, and a compare function that
         * compares the values of the two passed items for that key. For example:
         *
         * ```js
         * sortFn: (key) => (a, b) => {
         *     return a[key].localeCompare(b[key]);
         * }
         * ```
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
         * An optional callback function for sorting, primarily to be used for API calls
         * to retrieve sorted data from a backend and pass it back to the `items` prop.
         *
         * Must be a function that accepts two params: `field`, a string for the field to sort
         * on, and `direction`, which will be one of the numbers 0, -1, or 1.
         *
         * If you want to use this prop, you must also set the `useOnSort` prop to `true`.
         */
        onSort: {
            type: Function,
            default: () => {},
        },
        /**
         * Boolean indicating whether or not to use the `onSort` prop to sort items externally,
         * rather than on the frontend. Must be set `true` for the `onSort` prop to work.
         */
        useOnSort: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        return {
            sortState: {
                direction: 0,
            },
        };
    },
    computed: {
        /**
         * Get a copy of the items array, sorted by the selected column (if sort is
         * active) using either alphanumeric sort, or a supplied sort function.
         *
         * If `useOnSort` prop is set, just return the `items` array, since `onSort` is meant
         * to make an API call to mutate the original `items` array passed as a prop.
         */
        sortedItems() {
            if (!this.useOnSort && this.sortState.value && this.sortState.direction !== 0) {
                const alphabeticSort = (key) => (a, b) => {
                    return a[key].localeCompare(b[key]);
                };
                const sorted = [...this.items].sort(
                    this.sortState.sortFn
                        ? this.sortState.sortFn(this.sortState.value)
                        : alphabeticSort(this.sortState.value)
                );
                return this.sortState.direction === 1 ? sorted : sorted.reverse();
            } else {
                return this.items;
            }
        }
    },
    methods: {
        /**
         * When a header is clicked to change the sort state, update the sort state
         * accordingly.
         *
         * If the `onSort` prop is set, call it to make any API calls.
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
            if (this.useOnSort) {
                this.onSort(header.value, newDirection);
            }
        },
    },
}
</script>
