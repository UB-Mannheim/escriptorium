<script>
import '../Tags/Tag.css';
import './TagFilter.css';
import Tags from '../Tags/Tags.vue';
import Button from '../Button/Button.vue';
import ToggleButtonGroup from '../ToggleButtonGroup/ToggleButtonGroup.vue';

export default {
    name: 'escr-tag-filter',
    props: {
        /**
         * The list of tags, each an `Object` with a `name` (`String`) property
         * and a `variant` (`Number`) property, which must be between 1 and 12
         */
        tags: {
            type: Array,
            default: () => [],
            required: true,
            validator: function (value) {
                return value.length > 0 && value.every(t => t.name);
            },
        },
        /**
         * Tags that are already selected, as an array of names
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
            default: 'or',
        },
        /**
         * Boolean indicating whether or not "without tag" is already selected
         */
        withoutTagSelected: {
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
         *     withoutTag: Boolean,
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
            selectedTags: this.selected,
            selectedOperator: this.operator,
            withoutTag: this.withoutTagSelected,
        };
    },
    methods: {
        /**
         * Determine which variant class to apply based on props,
         * default variant is 12 (gray).
         */
        tagClasses: Tags.methods.tagClasses,
        /**
         * Change the operator for the filter (and/or)
         */
        setOperator: function (operator) {
            this.selectedOperator = operator;
        },
        /**
         * Select all tags after clicking "Select All"
         */
        selectAllTags: function () {
            this.selectedTags = this.tags.map(t => t.name);
        },
        /**
         * Select no tags after clicking "Select None"
         */
        selectNoTags: function () {
            this.selectedTags = [];
        },
        /**
         * Toggle "without tag" with the checkmark input
         */
        toggleWithoutTag: function (e) {
            this.withoutTag = e.target.checked;
        },
        /**
         * Helper method to render a checkbox input and label
         * for a given tag.
         */
        renderTagOption: function (h, tag) {
            return [
                h(
                    'input',
                    {
                        domProps: {
                            id: `filter-tag-${tag.name}`,
                            name: `filter-tag-${tag.name}`,
                            type: 'checkbox',
                            // ensure initial selections are checked on mount
                            checked: this.selectedTags.includes(tag.name),
                        },
                        on: {
                            change: (e) => {
                                // add or remove tags from selected list
                                if (e.target.checked) {
                                    this.selectedTags.push(tag.name);
                                } else {
                                    this.selectedTags.splice(
                                        this.selectedTags.indexOf(tag.name),
                                        1,
                                    );
                                }
                            }
                        },
                    },
                ),
                h(
                    'label',
                    {
                        class: this.tagClasses(tag.variant),
                        domProps: {
                            htmlFor: `filter-tag-${tag.name}`,
                        },
                    },
                    [h('span', tag.name)],
                ),
            ];
        },
        /**
         * Helper method to render cancel and apply buttons
         */
        renderFilterActions: function (h) {
            return h(
                'div',
                {
                    class: 'escr-filter-actions'
                },
                [
                    h(
                        Button,
                        {
                            props: {
                                color: 'outline-primary',
                                label: 'Cancel',
                                onClick: this.onCancel,
                            }
                        }
                    ),
                    h(
                        Button,
                        {
                            props: {
                                color: 'primary',
                                label: 'Apply Filter',
                                onClick: () => this.onApply({
                                    operator: this.selectedOperator,
                                    tags: this.selectedTags,
                                    withoutTag: this.withoutTag,
                                }),
                            }
                        }
                    ),
                ]
            );
        },
    },
    /**
     * Render the entire tag filter:
     * - And/or selector
     * - Buttons for select/deselect all
     * - TODO: Text input to filter tags by name
     * - A label and checkbox input for each tag
     * - A checkbox input for "without tag"
     * - Buttons to cancel and apply the filter
     */
    render: function (h) {
        return h(
            'div',
            { class: 'escr-tag-filter' },
            [
                h('h3', 'Filter Tags'),
                h(
                    ToggleButtonGroup,
                    {
                        props: {
                            color: 'secondary',
                            options: [{
                                value: 'and',
                                label: 'AND',
                            }, {
                                value: 'or',
                                label: 'OR',
                                selected: true,
                            }],
                            onChangeSelection: this.setOperator,
                        }
                    }
                ),
                h(
                    'h4',
                    [
                        h('span', 'Tags'),
                        h('div', [
                            h(Button, {
                                props: {
                                    label: 'Select All',
                                    color: 'link-primary',
                                    size: 'small',
                                    onClick: this.selectAllTags,
                                    disabled: this.selectedTags.length === this.tags.length,
                                },
                            }),
                            h(Button, {
                                props: {
                                    label: 'Select None',
                                    color: 'link-primary',
                                    size: 'small',
                                    onClick: this.selectNoTags,
                                    disabled: this.selectedTags.length === 0,
                                },
                            }),
                        ])
                    ]
                ),
                h(
                    'div',
                    { class: 'escr-tag-filter-group' },
                    this.tags.map((tag) => this.renderTagOption(h, tag)),
                ),
                h('hr'),
                h(
                    'label',
                    {
                        domProps: {
                            htmlFor: 'without-tag',
                        }
                    },
                    [
                        h(
                            'input',
                            {
                                domProps: {
                                    type: 'checkbox',
                                    id: 'without-tag',
                                    onchange: this.toggleWithoutTag
                                },
                            },
                        ),
                        h(
                            'span',
                            'Without tag'
                        )
                    ]
                ),
                this.renderFilterActions(h),
            ],
        );
    },
}
</script>
