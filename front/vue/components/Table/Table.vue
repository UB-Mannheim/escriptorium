<template>
    <table :class="classes">
        <!-- table head with (possibly sortable) labels -->
        <thead>
            <tr>
                <th
                    v-if="selectable"
                    class="escr-select-all"
                >
                    <label
                        class="escr-select-checkbox"
                        :disabled="disabled"
                        @click="onSelectAll"
                    >
                        <input
                            id="select-all"
                            class="sr-only"
                            type="checkbox"
                            name="select-all"
                            :checked="selectedItems && selectedItems.length > 0"
                            :disabled="disabled"
                        >
                        <CheckSquareIcon
                            class="unchecked"
                            aria-hidden="true"
                        />
                        <CheckSquareFilledIcon
                            class="checked"
                            aria-hidden="true"
                        />
                    </label>
                </th>
                <th
                    v-for="header in headers"
                    :key="header.key || header.value"
                    :class="getClasses(header)"
                >
                    <div>
                        <span v-if="!header.sortable">
                            {{ header.label }}
                        </span>
                        <!-- sort button -->
                        <button
                            v-else
                            class="escr-sort-button"
                            :disabled="disabled"
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
            <template
                v-for="(item, itemIndex) in items"
            >
                <!-- drop zone for table with orderable = true -->
                <tr
                    v-if="orderable"
                    :key="`order-before-${itemIndex}`"
                    class="escr-dropzone"
                >
                    <td
                        colspan="100%"
                        aria-hidden
                        :class="{
                            ['is-dragging']: isDragging,
                            ['drag-over']: dragOver === itemIndex,
                        }"
                        @dragover="(e) => handleDragOver(e, itemIndex)"
                        @dragenter="(e) => e.preventDefault()"
                        @dragleave="() => setDragOver(null)"
                        @drop="(e) => handleDrop(e, item, itemIndex)"
                        @mouseup="handleDragEnd"
                    />
                </tr>
                <!-- table row (with some drag'n'drop and selecting logic) -->
                <tr
                    v-if="item"
                    :key="item[itemKey]"
                    :draggable="draggedItem === itemIndex"
                    @dragstart="(e) => handleDragStart(e, item)"
                    @dragend="handleDragEnd"
                >
                    <!-- select checkbox -->
                    <td
                        v-if="selectable"
                        class="escr-select-column"
                    >
                        <div>
                            <!-- order drag handle -->
                            <div
                                v-if="orderable"
                                class="escr-drag-handle"
                                aria-hidden
                                @mousedown="() => handleDragMousedown(itemIndex)"
                                @mouseup="handleDragEnd"
                            >
                                <DragVerticalIcon />
                            </div>
                            <!-- select button -->
                            <label
                                :for="`select-${item[itemKey]}`"
                                class="escr-select-checkbox"
                                :disabled="disabled"
                                @click="(e) => onToggleSelected(
                                    e, parseInt(item[itemKey]), itemIndex + 1
                                )"
                            >
                                <input
                                    :id="`select-${item[itemKey]}`"
                                    class="sr-only"
                                    type="checkbox"
                                    :name="`select-${item[itemKey]}`"
                                    :disabled="disabled"
                                    :checked="selectedItems.includes(parseInt(item[itemKey]))"
                                >
                                <CheckSquareIcon
                                    class="unchecked"
                                    aria-hidden="true"
                                />
                                <CheckSquareFilledIcon
                                    class="checked"
                                    aria-hidden="true"
                                />
                            </label>
                        </div>
                    </td>
                    <!-- actual data for this row -->
                    <td
                        v-for="(header, index) in headers"
                        :key="header.key || header.value"
                        :class="getClasses(header)"
                    >
                        <div
                            v-if="!selectable && index === 0 && orderable"
                            class="escr-drag-handle"
                            aria-hidden
                            @mousedown="() => handleDragMousedown(itemIndex)"
                            @mouseup="handleDragEnd"
                        >
                            <DragVerticalIcon />
                        </div>
                        <img
                            v-if="header.image"
                            :src="item[header.image]"
                        >
                        <!-- linkable: component (e.g. tags) or simple span -->
                        <a
                            v-if="linkable && item.href && index == 0"
                            class="row-link"
                            :href="item.href"
                            :disabled="disabled"
                        >
                            <component
                                :is="header.component"
                                v-if="header.component && item[header.value]"
                                class="sr-only"
                                :disabled="disabled"
                                v-bind="item[header.value]"
                            />
                            <span
                                v-else
                                class="sr-only"
                            >
                                {{
                                    header.format
                                        ? header.format(item[header.value])
                                        : item[header.value]
                                }}
                            </span>
                        </a>
                        <!-- non-linkable: component or span -->
                        <component
                            :is="header.component"
                            v-if="header.component && item[header.value]"
                            v-bind="item[header.value]"
                            :disabled="disabled"
                        />
                        <input
                            v-else-if="header.editable && editingKey === item[itemKey].toString()"
                            type="text"
                            :value="item[header.value]"
                            :maxlength="512"
                            :disabled="disabled"
                            @input="(e) => onEdit({ field: header.value, value: e.target.value })"
                        >
                        <span
                            v-else
                        >
                            {{
                                header.format
                                    ? header.format(item[header.value])
                                    : item[header.value]
                            }}
                        </span>
                    </td>
                    <!-- row actions -->
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
                <!-- one extra drop zone after the bottom row -->
                <tr
                    v-if="orderable && itemIndex === items.length - 1"
                    :key="`order-after-${itemIndex}`"
                    class="escr-dropzone"
                >
                    <td
                        colspan="100%"
                        aria-hidden
                        :class="{
                            ['is-dragging']: isDragging,
                            ['drag-over']: dragOver === itemIndex + 1,
                        }"
                        @dragover="(e) => handleDragOver(e, itemIndex + 1)"
                        @dragenter="(e) => e.preventDefault()"
                        @dragleave="() => setDragOver(null)"
                        @drop="(e) => handleDrop(e, item, itemIndex + 1)"
                    />
                </tr>
            </template>
        </tbody>
    </table>
</template>
<script>
import CheckSquareIcon from "../Icons/CheckSquareIcon/CheckSquareIcon.vue";
import CheckSquareFilledIcon from "../Icons/CheckSquareFilledIcon/CheckSquareFilledIcon.vue";
import DragVerticalIcon from "../Icons/DragVerticalIcon/DragVerticalIcon.vue";
import SortIcon from "../Icons/SortIcon/SortIcon.vue";
import "./Table.css";

export default {
    name: "EscrTable",
    components: {
        CheckSquareIcon,
        CheckSquareFilledIcon,
        DragVerticalIcon,
        SortIcon,
    },
    props: {
        /**
         * An option to style this table as a compact table, which takes up less vertical space
         * and uses a smaller font size.
         */
        compact: {
            type: Boolean,
            default: false,
        },
        /**
         * Boolean indicating whether or not the sort buttons, links, select buttons, etc.
         * should be disabled, e.g. during loading.
         */
        disabled: {
            type: Boolean,
            default: false,
        },
        /**
         * If this table should have editable rows, this key should correspond to the row currently
         * being edited, or be empty.
         */
        editingKey: {
            type: String,
            default: "",
        },
        /**
         * List of headers, each of which is an object that should have a `value` and a `label`.
         * To make a column sortable, set the `sortable` boolean for its header to `true`.
         *
         * When using sortable columns, data may be sorted by using the callback function prop
         * `onSort` to mutate the `items` prop.
         *
         * If you need to apply formatting to a column, you can provide a `format` function in
         * the header object.
         *
         * You can also add a thumbnail image to a column by providing an `image` key, which should
         * match the key in each object containing an image URL.
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
         * Optional callback for additional logic on drag start, such as setting event data.
         */
        onDragStart: {
            type: Function,
            // eslint-disable-next-line no-unused-vars
            default: (e, item) => {},
        },
        /**
         * Required callback for drag-n-drop reordering; passed the drop event, the item being
         * dropped on, and the index of that item.
         */
        onDrop: {
            type: Function,
            // eslint-disable-next-line no-unused-vars
            default: (e, item, idx) => {},
        },
        /**
         * Callback for editing a field in a row. Currently only supports text.
         *
         * Must be a function that accepts a single object param with the following two keys:
         * `field`, a string for the field being edited, and
         * `value`, the new text value of the field.
         * It should be mapped back to the row item by the value of the `editingKey` prop.
         */
        onEdit: {
            type: Function,
            // eslint-disable-next-line no-unused-vars
            default: ({ field, value }) => {},
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
        /**
         * Callback function for selecting all items, for tables with `selectable` = `true`.
         */
        onSelectAll: {
            type: Function,
            default: () => {},
        },
        /**
         * Callback function for toggling a selected item, for tables with `selectable` = `true`.
         */
        onToggleSelected: {
            type: Function,
            default: () => {},
        },
        /**
         * Set `true` to allow reordering items by drag and drop.
         */
        orderable: {
            type: Boolean,
            default: false,
        },
        /**
         * Boolean indicating whether or not items should be selectable with checkbox inputs.
         */
        selectable: {
            type: Boolean,
            default: false,
        },
        /**
         * List of currently selected items, by key, for tables with `selectable` set `true`.
         */
        selectedItems: {
            type: Array,
            default: () => [],
        },
    },
    data() {
        return {
            sortState: {
                direction: 0,
            },
            dragOver: null,
            draggedItem: null,
            isDragging: false,
        };
    },
    computed: {
        classes() {
            return {
                "escr-table": true,
                "escr-table--selectable": this.selectable,
                "escr-table--compact": this.compact,
                "escr-table--orderable": this.orderable,
            };
        },
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
        /**
         * Apply with-img class to a th or td with images, and apply any other
         * classes supplied in the header.class property
         */
        getClasses(header) {
            const classes = {};
            if (header.image) classes["with-img"] = true
            if (header.class) classes[header.class] = true
            return classes;
        },
        /**
         * When one of this table's drop zones are dragged over, tell component which drop zone;
         * also, set the drop effect on the event
         */
        handleDragOver(e, idx) {
            e.preventDefault();
            this.setDragOver(idx);
            e.dataTransfer.dropEffect = "move";
        },
        /**
         * Set the component state to indicate whether or not a drop zone is being dragged over
         */
        setDragOver(idx) {
            this.dragOver = idx;
        },
        /**
         * Change the current value of isDragging in the component data.
         */
        setIsDragging(isDragging) {
            this.isDragging = isDragging;
        },
        /**
         * On dragging an item, create and set the drag image.
         */
        handleDragStart(e, item) {
            // timeout hack to prevent z-fighting with drop zones
            setTimeout(() => {
                this.setIsDragging(true);
            }, 200);
            // create a copy of this node
            const clonedNode = e.target.cloneNode(true);
            clonedNode.id = "is-drag-image";
            const style = getComputedStyle(e.target);
            const width = style.getPropertyValue("width");
            clonedNode.style.setProperty("max-width", width, "important");

            // if more than one selected, add the elements count label
            if (this.selectedItems && this.selectedItems.length > 1) {
                const elementsLabel = document.createElement("div");
                elementsLabel.innerText = `${this.selectedItems.length} elements`;
                elementsLabel.classList.add("elements-count");
                clonedNode.prepend(elementsLabel);
            }

            // add the overlay
            const overlay = document.createElement("div");
            overlay.classList.add("drag-overlay");
            clonedNode.appendChild(overlay);
            // append the cloned node to the DOM (it will be positioned offscreen)
            e.target.parentNode.appendChild(clonedNode);
            // call onDragStart after drag-image mounted, in case we want to change it
            this.onDragStart(e, item);
            // attach it to event as the drag image
            let mouseY = clonedNode.clientHeight / 2;
            if (this.selectedItems && this.selectedItems.length > 1) {
                mouseY += 20;
            }
            e.dataTransfer.setDragImage(clonedNode, 15, mouseY);
        },
        /**
         * Tell this component which child is being dragged; tell state that dragging has started
         */
        handleDragMousedown(idx) {
            this.draggedItem = idx;
        },
        /**
         * Tell this component that nothing is being dragged; tell state that dragging has stopped
         */
        handleDragEnd() {
            this.draggedItem = null;
            // clean up drag image if present (which has to be added to DOM, unfortunately!)
            const dragImage = document.getElementById("is-drag-image");
            if (dragImage) {
                dragImage.remove();
            }
            // timeout hack to prevent z-fighting with drag handle
            setTimeout(() => {
                this.setIsDragging(false);
            }, 100);
        },
        /**
         * On drop, perform the reordering operation, then turn off all drag-related
         * component and store states.
         */
        async handleDrop(e, item, idx) {
            await this.onDrop(e, item, idx);

            this.draggedItem = null;
            this.dragOver = null;
            // timeout hack to prevent z-fighting with drag handle
            setTimeout(() => {
                this.setIsDragging(false);
            }, 100);
        }
    },
}
</script>
