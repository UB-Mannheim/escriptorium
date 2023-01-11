<script>
import '../Tags/Tag.css';
import './TagFilter.css';
import Tags from '../Tags/Tags.vue';

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
         * Apply filter button behavior function
         */
        onApply: {
            type: Function,
            required: true,
        },
        /**
         * Cancel button behavior function
         */
        onCancel: {
            type: Function,
            required: true,
        },
    },
    methods: {
        /**
         * Determine which variant class to apply based on props,
         * default variant is 12 (gray).
         */
        tagClasses: Tags.methods.tagClasses,
        /**
         * Helper function to render a checkbox input and label
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
            ]
        }
    },
    /**
     * Render the entire tag filter:
     * - TODO: And/or selector
     * - TODO: Buttons for select/deselect all
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
                h('h4', 'Tags'),
                // h('button', 'Select All'),
                // h('button', 'Select None'),
                h(
                    'div',
                    { class: 'escr-tag-filter-group' },
                    this.tags.map((tag) => this.renderTagOption(h, tag)),
                ),
                h('hr'),
                h(
                    'input',
                    {
                        domProps: {
                            type: 'checkbox',
                            id: 'without-tag',
                        },
                    },
                ),
                h(
                    'label',
                    {
                        domProps: {
                            htmlFor: 'without-tag',
                        }
                    },
                    'Without tag'
                )
            ],
        );
    },
}
</script>
