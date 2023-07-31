<script>
import Button from "../Button/Button.vue";
import CheckIcon from "../Icons/CheckIcon/CheckIcon.vue";
import Tags from "../Tags/Tags.vue";
import TextField from "../TextField/TextField.vue";
import SegmentedButtonGroup from "../SegmentedButtonGroup/SegmentedButtonGroup.vue";
import "../Modal/Modal.css";
import "../Tags/Tag.css";
import "./TagFilter.css";

export default {
    name: "EscrTagFilter",
    props: {
        /**
         * The list of tags, each an `Object` with a `name` (`String`) property,
         * a `pk` (`Number`) property, and a `variant` (`Number`) property, which
         * must be between 1 and 12
         */
        tags: {
            type: Array,
            default: () => [],
            required: true,
            validator: function (value) {
                return value.length > 0 && value.every((t) => t.pk || t.pk === 0);
            },
        },
        /**
         * Tags that are already selected, as an array of pks
         */
        selected: {
            type: Array,
            default: () => [],
        },
        /**
         * Operator that is already selected
         */
        operator: {
            type: String,
            default: "or",
        },
        /**
         * Boolean indicating whether or not "untagged" is already selected
         */
        untaggedSelected: {
            type: Boolean,
            default: false,
        },
        /**
         * Behavior for the "apply filter" button. Should accept an object of the
         * following shape:
         *
         * ```
         * {
         *     operator: String,
         *     tags: Array<String>,
         *     untagged: Boolean,
         * }
         * ```
         */
        onApply: {
            type: Function,
            required: true,
        },
        /**
         * Behavior for the "cancel" button
         */
        onCancel: {
            type: Function,
            required: true,
        },
    },
    data: function () {
        return {
            selectedOperator: this.operator,
            selectedTags: [...this.selected],
            stringFilter: "",
            untagged: this.untaggedSelected,
        };
    },
    computed: {
        // Boolean indicating whether or not filter has been changed
        dirty() {
            const tagsChanged = !(
                this.selectedTags.every((tag) => this.selected.includes(tag))
                && this.selected.every((tag) => this.selectedTags.includes(tag))
            );
            return this.selectedOperator !== this.operator
                || this.untagged !== this.untaggedSelected
                || tagsChanged;
        }
    },
    methods: {
        /**
         * Determine which variant class to apply based on props,
         * default variant is 0 (gray).
         */
        tagClasses: Tags.methods.tagClasses,
        /**
         * Change the operator for the filter (and/or)
         */
        setOperator(operator) {
            this.selectedOperator = operator;
            if (operator === "and" && this.untagged) {
                this.untagged = false;
            }
        },
        /**
         * add or remove tags from selected list
         */
        changeTagSelection(checked, tag) {
            if (checked) {
                this.selectedTags.push(tag.pk);
            } else {
                this.selectedTags.splice(
                    this.selectedTags.indexOf(tag.pk),
                    1,
                );
            }
        },
        /**
         * Select all tags after clicking "Select All"
         */
        selectAllTags() {
            this.selectedTags = this.tags.map((t) => t.pk);
        },
        /**
         * Select no tags after clicking "Select None"
         */
        selectNoTags() {
            this.selectedTags = [];
        },
        /**
         * Toggle "untagged" with the checkmark input
         */
        toggleUntagged(e) {
            this.untagged = e.target.checked;
        },
        /**
         * Use the text input to filter the tags by string
         */
        filterByString(e) {
            this.stringFilter = e.target.value;
        },
        /**
         * Get the resulting tags after applying the string filter
         */
        getFilteredTags() {
            return this.tags.filter(
                (tag) =>
                    !this.stringFilter ||
                    tag.name.toLowerCase().includes(this.stringFilter.toLowerCase()),
            );
        },
        /**
         * Helper method to render a checkbox input and label
         * for a given tag.
         */
        renderTagOption(h, tag) {
            return [
                h(
                    "input",
                    {
                        class: {
                            "sr-only": true
                        },
                        domProps: {
                            id: `filter-tag-${tag.pk}`,
                            name: `filter-tag-${tag.pk}`,
                            type: "checkbox",
                            // ensure initial selections are checked on mount
                            checked: this.selectedTags.includes(tag.pk),
                        },
                        on: {
                            change: (e) => this.changeTagSelection(e.target.checked, tag),
                        },
                    },
                ),
                h(
                    "label",
                    {
                        class: this.tagClasses(tag.variant),
                        domProps: {
                            htmlFor: `filter-tag-${tag.pk}`,
                        },
                    },
                    [
                        h("span", tag.name),
                        h(CheckIcon)
                    ],
                ),
            ];
        },
        /**
         * Helper method to render cancel and apply buttons
         */
        renderFilterActions(h) {
            return h(
                "div",
                {
                    class: "modal-actions"
                },
                [
                    h(
                        Button,
                        {
                            props: {
                                color: "outline-primary",
                                label: "Cancel",
                                onClick: this.onCancel,
                            }
                        }
                    ),
                    h(
                        Button,
                        {
                            props: {
                                color: "primary",
                                label: "Apply Filter",
                                disabled: !this.dirty,
                                onClick: () => this.onApply({
                                    operator: this.selectedOperator,
                                    tags: this.selectedTags,
                                    untagged: this.untagged,
                                }),
                            }
                        }
                    ),
                ]
            );
        },
        /**
         * Helper method to render notice about tags hidden by string filter
         */
        renderFilteredTagNotice(h) {
            const filteredTags = this.getFilteredTags();
            const hiddenSelectedTagCount = this.tags.filter(
                (tag) =>
                    this.selectedTags.includes(tag.pk) &&
                    !filteredTags.some((t) => t.pk === tag.pk),
            ).length;
            if (filteredTags.length === 0) {
                return h(
                    "div",
                    `No matching tags. ${this.tags.length} tag${this.tags.length !== 1 ? "s" : ""
                    } hidden, including ${hiddenSelectedTagCount} selected.`,
                );
            } else if (filteredTags.length < this.tags.length) {
                const hiddenTagCount = this.tags.length - filteredTags.length;
                return h(
                    "div",
                    `+ ${hiddenTagCount
                    } tag${hiddenTagCount !== 1 ? "s" : ""} hidden, including ${
                        hiddenSelectedTagCount
                    } selected tag${hiddenSelectedTagCount !== 1 ? "s" : ""}`,
                );
            }
            return [];
        },
    },
    /**
     * Render the entire tag filter:
     * - And/or selector
     * - Buttons for select/deselect all
     * - Text input to filter tags by name
     * - A label and checkbox input for each tag
     * - A checkbox input for "untagged"
     * - Buttons to cancel and apply the filter
     */
    render(h) {
        return h(
            "div",
            { class: "escr-tag-filter escr-modal" },
            [
                h("h3", "Filter Tags"),
                h(
                    SegmentedButtonGroup,
                    {
                        props: {
                            color: "secondary",
                            name: "tag-filter-operator",
                            options: [{
                                value: "and",
                                label: "AND",
                                selected: this.selectedOperator === "and",
                            }, {
                                value: "or",
                                label: "OR",
                                selected: this.selectedOperator === "or",
                            }],
                            onChangeSelection: this.setOperator,
                        }
                    }
                ),
                h(
                    "h4",
                    [
                        h("span", "Tags"),
                        h("div", [
                            h(Button, {
                                props: {
                                    label: "Select All",
                                    color: "link-primary",
                                    size: "small",
                                    onClick: this.selectAllTags,
                                    disabled: this.selectedTags.length === this.tags.length,
                                },
                            }),
                            h(Button, {
                                props: {
                                    label: "Select None",
                                    color: "link-primary",
                                    size: "small",
                                    onClick: this.selectNoTags,
                                    disabled: this.selectedTags.length === 0,
                                },
                            }),
                        ])
                    ]
                ),
                h(
                    TextField,
                    {
                        props: {
                            label: "Find tag",
                            labelVisible: false,
                            onInput: this.filterByString,
                            placeholder: "Find tag",
                            value: this.stringFilter,
                        },
                    }
                ),
                h(
                    "div",
                    { class: "escr-tag-filter-group" },
                    this.getFilteredTags().map(
                        (tag) => this.renderTagOption(h, tag)
                    ),
                ),
                this.renderFilteredTagNotice(h),
                h("hr"),
                h(
                    "label",
                    {
                        domProps: {
                            htmlFor: "untagged",
                        }
                    },
                    [
                        h(
                            "input",
                            {
                                domProps: {
                                    type: "checkbox",
                                    id: "untagged",
                                    onchange: this.toggleUntagged,
                                    checked: this.untagged && this.selectedOperator !== "and",
                                    disabled: this.selectedOperator === "and",
                                },
                            },
                        ),
                        h(
                            "span",
                            "Untagged"
                        )
                    ]
                ),
                this.renderFilterActions(h),
            ],
        );
    },
}
</script>
