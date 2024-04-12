<template>
    <div
        :class="{
            'new-section': !toolbarDetached,
            'with-separator': !toolbarDetached,
            'detached-toolbar': toolbarDetached,
        }"
    >
        <div
            v-if="toolbarDetached"
            class="drag-handle"
            @pointerdown="startDrag"
        >
            <DragVerticalIcon />
        </div>
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

        <!-- selection-dependent tools -->
        <div
            v-if="hasSelection && !isDrawing"
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
                                v-for="(item, index) in typeOptions"
                                :key="item.pk"
                            >
                                <button
                                    :class="selectedType === item.name
                                        ? 'preselected'
                                        : ''"
                                    :disabled="disabled"
                                    @mousedown="() => clickSelectionType(item)"
                                >
                                    <span>
                                        {{ item.name }}{{
                                            index <= 9 ? ` (${index})` : ''
                                        }}
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
            v-if="hasSelection && !isDrawing"
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
                        <ul
                            id="delete-menu"
                            class="escr-vertical-menu"
                        >
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
                                            displayMode === "masks"
                                                ? "lines"
                                                : displayMode
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
        <VDropdown
            v-if="!toolbarDetached"
            theme="escr-tooltip-small"
            class="new-section with-separator"
            placement="bottom"
            :distance="8"
            :triggers="['hover']"
        >
            <EscrButton
                class="attach-detach-toolbar"
                color="text"
                :on-click="toggleToolbarDetached"
                :disabled="disabled"
            >
                <template #button-icon>
                    <DetachToolbarIcon />
                </template>
            </EscrButton>
            <template #popper>
                Detach toolbar
            </template>
        </VDropdown>
        <div
            v-else
            class="new-section with-separator"
        >
            <EscrButton
                color="text"
                class="attach-detach-toolbar"
                :on-click="toggleToolbarDetached"
                :disabled="disabled"
            >
                <template #button-icon>
                    <AttachToolbarIcon />
                </template>
            </EscrButton>
        </div>
    </div>
</template>
<script>
import { Dropdown as VDropdown, Menu as VMenu } from "floating-vue";
import { mapState } from "vuex";
import AttachToolbarIcon from "../Icons/AttachToolbarIcon/AttachToolbarIcon.vue";
import ChangeTypeIcon from "../Icons/ChangeTypeIcon/ChangeTypeIcon.vue";
import ChevronDownIcon from "../Icons/ChevronDownIcon/ChevronDownIcon.vue";
import DetachableMixin from "./DetachableMixin.vue";
import DetachToolbarIcon from "../Icons/DetachToolbarIcon/DetachToolbarIcon.vue";
import DragVerticalIcon from "../Icons/DragVerticalIcon/DragVerticalIcon.vue";
import EscrButton from "../Button/Button.vue";
import JoinIcon from "../Icons/JoinIcon/JoinIcon.vue";
import LineToolIcon from "../Icons/LineToolIcon/LineToolIcon.vue";
import LinkIcon from "../Icons/LinkIcon/LinkIcon.vue";
import RegionToolIcon from "../Icons/RegionToolIcon/RegionToolIcon.vue";
import ReverseIcon from "../Icons/ReverseIcon/ReverseIcon.vue";
import ScissorsIcon from "../Icons/ScissorsIcon/ScissorsIcon.vue";
import ToggleButton from "../ToggleButton/ToggleButton.vue";
import TrashIcon from "../Icons/TrashIcon/TrashIcon.vue";
import UnlinkIcon from "../Icons/UnlinkIcon/UnlinkIcon.vue";

export default {
    name: "EscrDetachableToolbar",
    components: {
        AttachToolbarIcon,
        ChangeTypeIcon,
        ChevronDownIcon,
        DetachToolbarIcon,
        DragVerticalIcon,
        EscrButton,
        JoinIcon,
        LineToolIcon,
        LinkIcon,
        RegionToolIcon,
        ReverseIcon,
        ScissorsIcon,
        ToggleButton,
        TrashIcon,
        UnlinkIcon,
        VDropdown,
        VMenu,
    },
    mixins: [DetachableMixin],
    props: {
        /**
         * Callback for pointerdown event to drag the detached toolbar
         */
        startDrag: {
            type: Function,
            default: () => {},
        },
        /**
         * True if a drawing is currently in progress, in which case the toolbar should
         * not add or remove icons.
         */
        isDrawing: {
            type: Boolean,
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
                    }
                }
            }
        }
    }
}
</script>
