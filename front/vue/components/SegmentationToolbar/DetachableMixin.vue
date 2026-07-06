<script>
/**
 * Mixin for the detachable toolbar, so that its props do not have to be repeated
 * between the attached and detached components.
 */
export default {
    props: {
        /**
         * True if all buttons and tools should be disabled
         */
        disabled: {
            type: Boolean,
            required: true,
        },
        /**
         * The current display mode, which should be one of "lines", "regions", or "masks"
         */
        displayMode: {
            type: String,
            required: true,
            validator(value) {
                return ["", "lines", "regions", "masks"].includes(value);
            },
        },
        /**
         * True if individual points (segments) are selected
         */
        hasPointsSelection: {
            type: Boolean,
            required: true,
        },
        /**
         * True if anything is selected (lines, regions, segments)
         */
        hasSelection: {
            type: Boolean,
            required: true,
        },
        /**
         * Callback function for changing the type of a selected line or region
         */
        onChangeSelectionType: {
            type: Function,
            required: true,
        },
        /**
         * Callback function for deleting a selected line, region, or segment
         * (should take an argument onlyPoints, which, if true, means only segments deleted)
         */
        onDelete: {
            type: Function,
            required: true,
        },
        /**
         * Callback function for joining selected lines
         */
        onJoin: {
            type: Function,
            required: true,
        },
        /**
         * Callback function for linking selected lines to regions
         */
        onLink: {
            type: Function,
            required: true,
        },
        /**
         * Callback function for reversing the direction of the selected line(s)
         */
        onReverse: {
            type: Function,
            required: true,
        },
        /**
         * Callback function for unlinking selected lines from regions
         */
        onUnlink: {
            type: Function,
            required: true,
        },
        /**
         * The currently selected type, which should be an object { name: String, pk: Number }
         */
        selectedType: {
            type: String,
            required: true,
        },
        /**
         * True if a region is linked to the currently selected line(s)
         */
        selectionIsLinked: {
            type: Boolean,
            required: true
        },
        /**
         * True if a region is not linked to the currently selected line(s)
         */
        selectionIsUnlinked: {
            type: Boolean,
            required: true
        },
        /**
         * Callback function to toggle one of the toggleable tools (cut, draw lines, draw regions)
         */
        toggleTool: {
            type: Function,
            required: true,
        },
        /**
         * Callback function to toggle the detached toolbar's detached state on and off
         */
        toggleToolbarDetached: {
            type: Function,
            required: true,
        },
        /**
         * True if the detachable toolbar is detached
         */
        toolbarDetached: {
            type: Boolean,
            required: true,
        },
        /**
         * Currently selected tool
         */
        tool: {
            type: String,
            required: true,
        },
    },
};
</script>
