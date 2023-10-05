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

                <!-- toggle line numbers -->
                <VDropdown
                    id="line-numbers-toggle"
                    class="new-section"
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
                            <LineNumberingIcon />
                        </template>
                    </ToggleButton>
                    <template #popper>
                        Line numbering (L)
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

                <!-- mode-dependent tools -->
                <div
                    class="new-section with-separator"
                >
                    <!-- add line tool -->
                    <VDropdown
                        v-if="displayMode === 'lines'"
                        id="add-lines"
                        theme="escr-tooltip-small"
                        placement="bottom"
                        :distance="8"
                        :triggers="['hover']"
                    >
                        <ToggleButton
                            color="text"
                            :checked="tool === 'add-lines'"
                            :disabled="disabled"
                            :on-change="() => toggleTool('add-lines')"
                        >
                            <template #button-icon>
                                <LineToolIcon />
                            </template>
                        </ToggleButton>
                        <template #popper>
                            Add lines (A)
                        </template>
                    </VDropdown>

                    <!-- add region tool -->
                    <VDropdown
                        v-else-if="displayMode === 'regions'"
                        id="add-regions"
                        theme="escr-tooltip-small"
                        placement="bottom"
                        :distance="8"
                        :triggers="['hover']"
                    >
                        <ToggleButton
                            color="text"
                            :checked="tool === 'add-regions'"
                            :disabled="disabled"
                            :on-change="() => toggleTool('add-regions')"
                        >
                            <template #button-icon>
                                <RegionToolIcon />
                            </template>
                        </ToggleButton>
                        <template #popper>
                            Add region (A)
                        </template>
                    </VDropdown>

                    <!-- cut tool -->
                    <VDropdown
                        theme="escr-tooltip-small"
                        placement="bottom"
                        :distance="8"
                        :triggers="['hover']"
                    >
                        <ToggleButton
                            color="text"
                            :checked="tool === 'cut'"
                            :disabled="disabled"
                            :on-change="() => toggleTool('cut')"
                        >
                            <template #button-icon>
                                <ScissorsIcon />
                            </template>
                        </ToggleButton>
                        <template #popper>
                            Cut (C)
                        </template>
                    </VDropdown>
                </div>

                <!-- selection-dependent tools -->
                <div
                    v-if="hasSelection"
                    class="new-section with-separator"
                >
                    <!-- link/unlink -->
                    <VDropdown
                        v-if="['lines', 'masks'].includes(displayMode)"
                        theme="escr-tooltip-small"
                        placement="bottom"
                        :distance="8"
                        :triggers="['hover']"
                    >
                        <EscrButton
                            color="text"
                            :aria-label="linkUnlinkTooltip"
                            :on-click="onLinkUnlink"
                            :disabled="disabled"
                        >
                            <template #button-icon>
                                <UnlinkIcon v-if="selectionIsLinked" />
                                <LinkIcon v-else />
                            </template>
                        </EscrButton>
                        <template #popper>
                            <div class="escr-toolbar-tooltip">
                                {{ linkUnlinkTooltip }}
                            </div>
                        </template>
                    </VDropdown>

                    <!-- join (merge) -->
                    <VDropdown
                        v-if="['lines', 'masks'].includes(displayMode)"
                        theme="escr-tooltip-small"
                        placement="bottom"
                        :distance="8"
                        :triggers="['hover']"
                    >
                        <EscrButton
                            aria-label="Join selected lines"
                            color="text"
                            :on-click="onJoin"
                            :disabled="disabled"
                        >
                            <template #button-icon>
                                <JoinIcon />
                            </template>
                        </EscrButton>
                        <template #popper>
                            Join selected lines (J)
                        </template>
                    </VDropdown>

                    <!-- reverse direction -->
                    <VDropdown
                        v-if="['lines', 'masks'].includes(displayMode)"
                        theme="escr-tooltip-small"
                        placement="bottom"
                        :distance="8"
                        :triggers="['hover']"
                    >
                        <EscrButton
                            aria-label="Reverse selected lines"
                            color="text"
                            :on-click="onReverse"
                            :disabled="disabled"
                        >
                            <template #button-icon>
                                <ReverseIcon />
                            </template>
                        </EscrButton>
                        <template #popper>
                            Reverse selected lines (I)
                        </template>
                    </VDropdown>

                    <!-- change type -->
                    <VDropdown
                        theme="escr-tooltip-small"
                        placement="bottom"
                        :distance="8"
                        :triggers="['hover']"
                    >
                        <VMenu
                            theme="vertical-menu"
                            placement="bottom"
                            :delay="{ show: 0, hide: 100 }"
                            :distance="8"
                            :shown="typeMenuOpen"
                            :triggers="[]"
                            :auto-hide="true"
                            @apply-hide="closeTypeMenu"
                        >
                            <EscrButton
                                aria-label="Change type"
                                color="text"
                                :on-click="openTypeMenu"
                                :disabled="disabled"
                            >
                                <template #button-icon>
                                    <ChangeTypeIcon />
                                </template>
                            </EscrButton>
                            <template #popper>
                                <ul
                                    id="type-select-menu"
                                    class="escr-vertical-menu"
                                >
                                    <li
                                        v-for="item in typeOptions"
                                        :key="item.pk"
                                    >
                                        <button
                                            :class="selectedType === item.name ? 'preselected' : ''"
                                            :disabled="disabled"
                                            @mousedown="() => clickSelectionType(item)"
                                        >
                                            <span>
                                                {{ item.name }}
                                            </span>
                                        </button>
                                    </li>
                                </ul>
                            </template>
                        </VMenu>
                        <template #popper>
                            Set type of selected {{
                                displayMode === "masks" ? "lines" : displayMode
                            }} (T)
                        </template>
                    </VDropdown>
                </div>
                <div
                    v-if="hasSelection"
                    class="new-section with-separator"
                >
                    <!-- delete -->
                    <VDropdown
                        theme="escr-tooltip-small"
                        placement="bottom"
                        :distance="8"
                        :triggers="['hover']"
                    >
                        <VMenu
                            theme="vertical-menu"
                            placement="bottom"
                            :delay="{ show: 0, hide: 100 }"
                            :distance="8"
                            :shown="deleteMenuOpen"
                            :triggers="[]"
                            :auto-hide="true"
                            @apply-hide="closeDeleteMenu"
                        >
                            <EscrButton
                                id="escr-delete-dropdown-button"
                                aria-label="Delete lines/regions/points"
                                color="text"
                                :on-click="openDeleteMenu"
                                :disabled="disabled"
                            >
                                <template #button-icon>
                                    <TrashIcon />
                                    <ChevronDownIcon />
                                </template>
                            </EscrButton>
                            <template #popper>
                                <ul class="escr-vertical-menu">
                                    <li v-if="hasPointsSelection">
                                        <button
                                            :disabled="disabled"
                                            @mousedown="() => clickDelete(true)"
                                        >
                                            <span>Delete selected points (Ctrl Del)</span>
                                        </button>
                                    </li>
                                    <li>
                                        <button
                                            :disabled="disabled"
                                            @mousedown="() => clickDelete(false)"
                                        >
                                            <span>
                                                Delete all selected {{
                                                    displayMode === "masks" ? "lines" : displayMode
                                                }} (Del)
                                            </span>
                                        </button>
                                    </li>
                                </ul>
                            </template>
                        </VMenu>
                        <template #popper>
                            Delete selection
                        </template>
                    </VDropdown>
                </div>
            </div>
        </template>
    </EditorToolbar>
</template>

<script>
import ChangeTypeIcon from "../Icons/ChangeTypeIcon/ChangeTypeIcon.vue";
import ChevronDownIcon from "../Icons/ChevronDownIcon/ChevronDownIcon.vue";
import EditorToolbar from "../EditorToolbar/EditorToolbar.vue";
import EscrButton from "../Button/Button.vue";
import JoinIcon from "../Icons/JoinIcon/JoinIcon.vue";
import LineNumberingIcon from "../Icons/LineNumberingIcon/LineNumberingIcon.vue";
import LineToolIcon from "../Icons/LineToolIcon/LineToolIcon.vue";
import LinesIcon from "../Icons/LinesIcon/LinesIcon.vue";
import LinkIcon from "../Icons/LinkIcon/LinkIcon.vue";
import MasksIcon from "../Icons/MasksIcon/MasksIcon.vue";
import RedoIcon from "../Icons/RedoIcon/RedoIcon.vue";
import RegionToolIcon from "../Icons/RegionToolIcon/RegionToolIcon.vue";
import RegionsIcon from "../Icons/RegionsIcon/RegionsIcon.vue";
import ReverseIcon from "../Icons/ReverseIcon/ReverseIcon.vue";
import ScissorsIcon from "../Icons/ScissorsIcon/ScissorsIcon.vue";
import SegmentedButtonGroup from "../SegmentedButtonGroup/SegmentedButtonGroup.vue";
import ToggleButton from "../ToggleButton/ToggleButton.vue";
import TrashIcon from "../Icons/TrashIcon/TrashIcon.vue";
import UndoIcon from "../Icons/UndoIcon/UndoIcon.vue";
import UnlinkIcon from "../Icons/UnlinkIcon/UnlinkIcon.vue";
import { Dropdown as VDropdown, Menu as VMenu } from "floating-vue";
import { mapState } from "vuex";
import "../VerticalMenu/VerticalMenu.css";
import "./SegmentationToolbar.css";

export default {
    name: "EscrSegmentationToolbar",
    components: {
        ChangeTypeIcon,
        ChevronDownIcon,
        EditorToolbar,
        EscrButton,
        JoinIcon,
        LineNumberingIcon,
        LineToolIcon,
        LinkIcon,
        RedoIcon,
        RegionToolIcon,
        ReverseIcon,
        ScissorsIcon,
        SegmentedButtonGroup,
        ToggleButton,
        TrashIcon,
        UndoIcon,
        UnlinkIcon,
        VDropdown,
        VMenu,
    },
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
         * Callback function for linking/unlinking selected lines to/from regions
         */
        onLinkUnlink: {
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
         * Callback function for reversing the direction of the selected line(s)
         */
        onReverse: {
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
         * Callback function to toggle one of the toggleable tools (cut, draw lines, draw regions)
         */
        toggleTool: {
            type: Function,
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
    data() {
        return {
            deleteMenuOpen: false,
            typeMenuOpen: false,
        }
    },
    computed: {
        ...mapState({
            blockShortcuts: (state) => state.document.blockShortcuts,
            lineTypes: (state) => state.document.types.lines,
            regionTypes: (state) => state.document.types.regions,
        }),
        /**
         * Get objects for the three modes (lines, regions, masks)
         */
        modeOptions() {
            return [
                {
                    value: "lines",
                    label: LinesIcon,
                    selected: this.displayMode === "lines",
                    tooltip: "Lines mode",
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
        /**
         * String for the link/unlink tooltip depending on current state
         */
        linkUnlinkTooltip() {
            if (this.selectionIsLinked) {
                return "Unlink selected lines from region (U)";
            } else {
                return "Link selected lines to the first detected background region (Y)";
            }
        },
        /**
         * Current available types with "None" appended at the beginning
         */
        typeOptions() {
            if (this.displayMode === "regions") {
                return [{name: "None"}].concat(this.regionTypes);
            }
            return [{name: "None"}].concat(this.lineTypes);
        },
    },
    mounted() {
        // on mount, add keyboard event listeners for selecting a type
        document.addEventListener("keydown", this.typeSelectKeydown.bind(this));
    },
    methods: {
        /**
         * Callback to close the delete menu
         */
        closeDeleteMenu() {
            this.deleteMenuOpen = false;
        },
        /**
         * Callback to close the type select menu
         */
        closeTypeMenu() {
            this.typeMenuOpen = false;
        },
        /**
         * On click, call the callback for deleting a selection, and close the type menu
         *
         * @param {Boolean} onlyPoints True if only points (segments) should be deleted
         */
        clickDelete(onlyPoints) {
            this.onDelete(onlyPoints);
            this.closeDeleteMenu();
        },
        /**
         * On click, call the callback for changing selection type and close the type menu
         *
         * @param {*} item An object with at least a "name" String property
         */
        clickSelectionType(item) {
            this.onChangeSelectionType(item.name);
            this.closeTypeMenu();
        },
        /**
         * Callback to open the delete menu
         */
        openDeleteMenu() {
            this.deleteMenuOpen = true;
        },
        /**
         * Callback to open the type select menu
         */
        openTypeMenu() {
            this.typeMenuOpen = true;
        },
        /**
         * Keyboard event handler for type select
         * @param {KeyboardEvent} evt
         */
        typeSelectKeydown(evt) {
            if (!this.blockShortcuts) {
                // on keydown, if the type menu is open, listen for numerals
                if (this.typeMenuOpen) {
                    const num = Number(evt.key);
                    const types = this.typeOptions;
                    // if it's a number, and in the range of indices, select the type at that index
                    if (!isNaN(num) && num < types.length) {
                        this.clickSelectionType(types[num]);
                    } else if (evt.key === "t") {
                        this.closeTypeMenu();
                    }
                } else {
                    if (evt.key === "t" && this.hasSelection) {
                        this.openTypeMenu();
                    } else if (evt.key === "c") {
                        this.toggleTool("cut");
                    }
                }
            }
        }
    }
}
</script>
