<template>
    <EditorToolbar
        panel-type="segmentation"
        :disabled="disabled"
        :panel-index="panelIndex"
    >
        <template #editor-tools-center>
            <div class="escr-editortools-paneltools">
                <!-- change view mode -->
                <SegmentedButtonGroup
                    color="secondary"
                    name="segmentation-view-mode"
                    :disabled="disabled"
                    :options="modeOptions"
                    :on-change-selection="onChangeMode"
                />
                <!-- grouped toggles: line numbers, auto-order, manual-order -->
                <div class="seg-toolbar-btn-group new-section">
                    <!-- toggle line numbers -->
                    <VDropdown
                        id="line-numbers-toggle"
                        theme="escr-tooltip-small"
                        placement="bottom"
                        :distance="8"
                        :triggers="['hover']"
                    >
                        <ToggleButton
                            color="primary"
                            :checked="lineNumberingEnabled"
                            :disabled="disabled"
                            :on-change="onToggleLineNumbering"
                        >
                            <template #button-icon>
                                <LineNumberingIcon style="width: 24px; height: 24px;" />
                            </template>
                        </ToggleButton>
                        <template #popper>
                            Line numbering (N)
                        </template>
                    </VDropdown>
                    <VDropdown
                        id="toggle-auto-order"
                        theme="escr-tooltip-small"
                        placement="bottom"
                        :distance="8"
                        :triggers="['hover']"
                    >
                        <ToggleButton
                            color="primary"
                            :checked="autoOrder"
                            :disabled="disabled"
                            :on-change="onToggleAutoOrder"
                        >
                            <template #button-icon>
                                <i class="fas fa-robot" />
                            </template>
                        </ToggleButton>
                        <template #popper>
                            Toggle automatic reordering on line creation/deletion.
                        </template>
                    </VDropdown>
                    <!-- manual reorder when auto-order off -->
                    <VDropdown
                        v-if="!autoOrder"
                        id="manual-order"
                        theme="escr-tooltip-small"
                        placement="bottom"
                        :distance="8"
                        :triggers="['hover']"
                    >
                        <EscrButton
                            aria-label="reorder lines"
                            color="primary"
                            :on-click="onRecalculateOrdering"
                            :disabled="disabled"
                        >
                            <template #button-icon>
                                <i class="fas fa-magic"></i>
                            </template>
                        </EscrButton>
                        <template #popper>
                            Reorder lines manually
                        </template>
                    </VDropdown>
                </div>
                <!-- calculate masks -->
                <VDropdown
                    v-if="!hasMasks && lines.length > 0"
                    class="new-section"
                    theme="escr-tooltip-small"
                    placement="bottom"
                    :distance="8"
                    :triggers="['hover']"
                >
                    <EscrButton
                        aria-label="calculate masks"
                        color="primary"
                        :on-click="processLines"
                        :disabled="disabled"
                    >
                        <template #button-icon>
                            <i class="fas fa-thumbs-up" />
                        </template>
                    </EscrButton>
                    <template #popper>
                        Calculate masks
                    </template>
                </VDropdown>

                <!-- undo/redo -->
                <VDropdown
                    id="undo"
                    theme="escr-tooltip-small"
                    class="new-section"
                    placement="bottom"
                    :distance="8"
                    :triggers="['hover']"
                >
                    <EscrButton
                        id="undo-button"
                        aria-label="undo"
                        color="text"
                        :on-click="onUndo"
                        :disabled="disabled || !canUndo"
                    >
                        <template #button-icon>
                            <UndoIcon />
                        </template>
                    </EscrButton>
                    <template #popper>
                        Undo (Ctrl Z)
                    </template>
                </VDropdown>
                <VDropdown
                    id="redo"
                    theme="escr-tooltip-small"
                    placement="bottom"
                    :distance="8"
                    :triggers="['hover']"
                >
                    <EscrButton
                        id="redo-button"
                        aria-label="redo"
                        color="text"
                        :on-click="onRedo"
                        :disabled="disabled || !canRedo"
                    >
                        <template #button-icon>
                            <RedoIcon />
                        </template>
                    </EscrButton>
                    <template #popper>
                        Redo (Ctrl Y)
                    </template>
                </VDropdown>
                <DetachableToolbar
                    v-if="!toolbarDetached"
                    :disabled="disabled"
                    :display-mode="displayMode"
                    :has-points-selection="hasPointsSelection"
                    :has-selection="hasSelection"
                    :is-drawing="isDrawing"
                    :region-labels-enabled="regionLabelsEnabled"
                    :on-toggle-region-labels="onToggleRegionLabels"
                    :on-change-selection-type="onChangeSelectionType"
                    :on-delete="onDelete"
                    :on-join="onJoin"
                    :on-link="onLink"
                    :on-unlink="onUnlink"
                    :on-reverse="onReverse"
                    :selected-type="selectedType"
                    :selection-is-linked="selectionIsLinked"
                    :selection-is-unlinked="selectionIsUnlinked"
                    :toggle-tool="toggleTool"
                    :toggle-toolbar-detached="toggleToolbarDetached"
                    :tool="tool"
                    :toolbar-detached="false"
                />
            </div>
        </template>
    </EditorToolbar>
</template>

<script>
import { mapState, mapGetters } from "vuex";
import DetachableMixin from "./DetachableMixin.vue";
import DetachableToolbar from "./DetachableToolbar.vue";
import EditorToolbar from "../EditorToolbar/EditorToolbar.vue";
import EscrButton from "../Button/Button.vue";
import LineNumberingIcon from "../Icons/LineNumberingIcon/LineNumberingIcon.vue";
import LinesIcon from "../Icons/LinesIcon/LinesIcon.vue";
import MasksIcon from "../Icons/MasksIcon/MasksIcon.vue";
import RedoIcon from "../Icons/RedoIcon/RedoIcon.vue";
import RegionsIcon from "../Icons/RegionsIcon/RegionsIcon.vue";
import SegmentedButtonGroup from "../SegmentedButtonGroup/SegmentedButtonGroup.vue";
import ToggleButton from "../ToggleButton/ToggleButton.vue";
import UndoIcon from "../Icons/UndoIcon/UndoIcon.vue";
import { Dropdown as VDropdown } from "floating-vue";
import "../VerticalMenu/VerticalMenu.css";
import "./SegmentationToolbar.css";

export default {
    name: "EscrSegmentationToolbar",
    components: {
        DetachableToolbar,
        EditorToolbar,
        EscrButton,
        LineNumberingIcon,
        RedoIcon,
        SegmentedButtonGroup,
        ToggleButton,
        UndoIcon,
        VDropdown,
    },
    mixins: [DetachableMixin],
    props: {
        /**
         * True if redo is currently possible
         */
        canRedo: {
            type: Boolean,
            required: true,
        },
        /**
         * True if undo is currently possible
         */
        canUndo: {
            type: Boolean,
            required: true,
        },
        /**
         * True if a drawing is currently in progress, in which case the toolbar should
         * not add or remove icons.
         */
        isDrawing: {
            type: Boolean,
            required: true,
        },
        /**
         * True if line numbering is currently toggled on
         */
        lineNumberingEnabled: {
            type: Boolean,
            required: true,
        },
        /**
         * Callback function for changing the display mode
         */
        onChangeMode: {
            type: Function,
            required: true,
        },
        /**
         * Callback function for turning line numbering on and off
         */
        onToggleLineNumbering: {
            type: Function,
            required: true,
        },
        /**
         * Callback function for redo
         */
        onRedo: {
            type: Function,
            required: true,
        },
        /**
         * Callback function for undo
         */
        onUndo: {
            type: Function,
            required: true,
        },
        /**
         * The index of this panel, to allow swapping in EditorToolbar dropdown
         */
        panelIndex: {
            type: Number,
            required: true,
        },
        processLines: {
            type: Function,
            required: true,
        },
        autoOrder: {
            type: Boolean,
            required: true
        },
        onToggleAutoOrder: {
            type: Function,
            required: true
        },
        onRecalculateOrdering: {
            type: Function,
            required: true
        },
        regionLabelsEnabled: {
            type: Boolean,
            required: true,
            default: false,
        },
        onToggleRegionLabels: {
            type: Function,
            required: true,
            default: () => {},
        },

    },
    computed: {
        ...mapState({
            "lines": (state) => state.lines.all,
        }),
        ...mapGetters("lines", ["hasMasks"]),
        /**
         * Get objects for the three modes (lines, regions, masks)
         */
        modeOptions() {
            return [
                {
                    value: "lines",
                    label: LinesIcon,
                    selected: this.displayMode === "lines",
                    tooltip: "Lines mode (L)",
                },
                {
                    value: "masks",
                    label: MasksIcon,
                    selected: this.displayMode === "masks",
                    tooltip: "Masks mode (M)",
                },
                {
                    value: "regions",
                    label: RegionsIcon,
                    selected: this.displayMode === "regions",
                    tooltip: "Regions mode (R)",
                },
            ]
        },
    },
}
</script>
