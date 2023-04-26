<script>
import CheckIcon from "../Icons/CheckIcon/CheckIcon.vue";
import EscrButton from "../Button/Button.vue";
import Tags from "../Tags/Tags.vue";
import TextField from "../TextField/TextField.vue";
import "./TagsField.css";
import PlusIcon from "../Icons/PlusIcon/PlusIcon.vue";

export default {
    name: "EscrTagsField",
    props: {
        disabled: {
            type: Boolean,
            required: true,
        },
        onChange: {
            type: Function,
            required: true,
        },
        onChangeTagName: {
            type: Function,
            required: true,
        },
        onCreateTag: {
            type: Function,
            required: true,
        },
        tagName: {
            type: String,
            required: true,
        },
        tags: {
            type: Array,
            required: true,
        },
        selectedTags: {
            type: Array,
            required: true,
        },
    },
    computed: {
        filteredTags() {
            return this.tags?.filter(
                (tag) => tag.name?.toLowerCase().includes(this.tagName?.toLowerCase())
            ) || [];
        },
    },
    methods: {
        /**
         * Determine which variant class to apply based on props,
         * default variant is 12 (gray).
         */
        tagClasses: Tags.methods.tagClasses,
        /*
         * Helper method to render an individual tag option
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
                            id: `field-tag-${tag.pk}`,
                            name: `field-tag-${tag.pk}`,
                            type: "checkbox",
                            // ensure initial selections are checked on mount
                            checked: this.selectedTags.includes(tag.pk),
                        },
                        on: {
                            change: (e) => this.onChange({ checked: e.target.checked, tag }),
                        },
                    },
                ),
                h(
                    "label",
                    {
                        class: this.tagClasses(tag.variant),
                        domProps: {
                            htmlFor: `field-tag-${tag.pk}`,
                        },
                    },
                    [
                        h("span", tag.name),
                        h(CheckIcon)
                    ],
                ),
            ];
        },
        /*
         * Helper method to render notice about tags hidden by string filter
         */
        renderFilteredTagNotice(h) {
            const filteredTags = this.filteredTags;
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
        /*
         * Helper method to render the "add tag" button
         */
        renderAddTagButton(h) {
            return h(
                "div",
                { class: "escr-create-tag" },
                [
                    h(
                        EscrButton,
                        {
                            props: {
                                color: "text",
                                label: this.tagName
                                    ? `Create a tag "${this.tagName}"`
                                    : "Create a tag",
                                disabled: this.disabled || !this.tagName || this.tags.some(
                                    (tag) => tag.name === this.tagName
                                ),
                                onClick: this.onCreateTag,
                                size: "small",
                            },
                            scopedSlots: {
                                "button-icon": () => {
                                    return h(PlusIcon)
                                },
                            },
                        },
                    )]
            );
        },
    },
    render(h) {
        return h(
            "div",
            { class: "escr-tags-field escr-form-field" },
            [
                h("span", { class: "escr-form-label" }, "Tags"),
                h(
                    TextField,
                    {
                        props: {
                            label: "Add/search tags",
                            labelVisible: false,
                            onInput: this.onChangeTagName,
                            placeholder: "Add/search tags",
                            value: this.tagName,
                        },
                    }
                ),
                h(
                    "div",
                    { class: "escr-tag-field-group" },
                    [...this.filteredTags].sort(
                        (a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase())
                    ).map(
                        (tag) => this.renderTagOption(h, tag)
                    ),
                ),
                this.renderFilteredTagNotice(h),
                this.renderAddTagButton(h),
            ],
        );
    },
}
</script>
