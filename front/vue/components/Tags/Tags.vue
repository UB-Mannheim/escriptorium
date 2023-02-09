<template>
    <div :class="classes">
        <span
            v-for="tag in tags"
            :key="tag.name"
            :class="tagClasses(tag.variant)"
        >
            {{ tag.name }}
        </span>
        <!-- Tag overflow toggle for non-wrapping tag group -->
        <div
            v-if="!wrap && shouldOverflow"
            :class="tagClasses()"
            class="escr-tag-overflow-toggle"
            @mouseover="showOverflowed"
            @mouseout="hideOverflowed"
        >
            <span>...</span>
            <!-- Tag overflow list -->
            <div
                v-if="overflowVisible"
                class="escr-tag-overflow"
            >
                <span
                    v-for="tag in overflowTags"
                    :key="tag.name"
                    :class="tagClasses(tag.variant)"
                >
                    {{ tag.name }}
                </span>
            </div>
        </div>
    </div>
</template>
<script>
import "./Tag.css";
import "./TagGroup.css";

export default {
    name: "EscrTags",

    props: {
        /**
         * The list of tags, each an `Object` with a `name` (`String`) property
         * and a `variant` (`Number`) property, which must be between 1 and 12
         */
        tags: {
            type: Array,
            default: () => [],
            required: true,
            validator(value) {
                return value.length > 0 && value.every((t) => t.name);
            },
        },
        /**
         * Whether or not the list of tags should wrap onto new lines
         */
        wrap: {
            type: Boolean,
            default: false,
        },
    },

    data() {
        return {
            shouldOverflow: false,
            overflowVisible: false,
            overflowTags: [],
        };
    },

    computed: {
        classes() {
            return {
                "escr-tag-group": true,
                "escr-tag-group-wrapped": this.wrap,
            };
        },
    },
    /**
     * On mount, if this tag group is not meant to wrap, calculate which tags
     * need to go into the overflow menu, remove them from the visible portion,
     * and add them into the overflow tags list.
     */
    async mounted() {
        await this.$nextTick();
        if (!this.wrap) {
            const parentWidth = this.$el.parentElement.clientWidth;
            let childrenWidth = 0;
            this.tags.forEach((tag, i) => {
                const childElement = this.$el.childNodes[i];
                // add up each element's width + 4px margin per element
                childrenWidth += childElement.scrollWidth + 4;
                if ((childrenWidth + 36) >= parentWidth) {
                    // hide child element and add tag to list
                    childElement.style.display = "none";
                    this.shouldOverflow = true;
                    this.overflowTags.push(tag);
                }
            });
        }
    },
    methods: {
        /**
         * Determine which variant class to apply based on props,
         * default variant is 12 (gray).
         */
        tagClasses(variant) {
            return {
                "escr-tag": true,
                [`escr-tag--variant-${variant || 12}`]: true,
            };
        },
        /**
         * On hovering the "overflow toggle", show the overflow list.
         */
        showOverflowed() {
            this.overflowVisible = true;
        },
        /**
         * On leaving the "overflow toggle", hide the overflow list.
         */
        hideOverflowed() {
            this.overflowVisible = false;
        },
    }

}

</script>
