<template>
    <div class="escr-toolbar escr-editor-global-toolbar">
        <VDropdown
            theme="escr-tooltip-small"
            placement="bottom"
            :distance="8"
            :triggers="['hover']"
        >
            <ToggleButton
                id="escr-toggle-select"
                color="text"
                :checked="tool === 'select'"
                :disabled="disabled"
                :on-change="() => toggleTool('select')"
            >
                <template #button-icon>
                    <CursorSelectIcon />
                </template>
            </ToggleButton>
            <template #popper>
                Select (S)
            </template>
        </VDropdown>
        <VDropdown
            theme="escr-tooltip-small"
            placement="bottom"
            :distance="8"
            :triggers="['hover']"
        >
            <ToggleButton
                id="escr-toggle-pan"
                color="text"
                :checked="tool === 'pan'"
                :disabled="disabled"
                :on-change="() => toggleTool('pan')"
            >
                <template #button-icon>
                    <CursorPanIcon />
                </template>
            </ToggleButton>
            <template #popper>
                Pan (H)
            </template>
        </VDropdown>
        <div class="new-section with-separator">
            <VDropdown
                theme="escr-tooltip-small"
                placement="bottom"
                :distance="8"
                :triggers="['hover']"
            >
                <EscrButton
                    aria-label="Zoom in"
                    color="text"
                    :on-click="onZoomIn"
                    :disabled="disabled"
                >
                    <template #button-icon>
                        <ZoomInIcon />
                    </template>
                </EscrButton>
                <template #popper>
                    Zoom in (Ctrl +)
                </template>
            </VDropdown>
            <VDropdown
                theme="escr-tooltip-small"
                placement="bottom"
                :distance="8"
                :triggers="['hover']"
            >
                <EscrButton
                    aria-label="Zoom out"
                    color="text"
                    :on-click="onZoomOut"
                    :disabled="disabled"
                >
                    <template #button-icon>
                        <ZoomOutIcon />
                    </template>
                </EscrButton>
                <template #popper>
                    Zoom out (Ctrl -)
                </template>
            </VDropdown>
            <VDropdown
                theme="escr-tooltip-small"
                placement="bottom"
                :distance="8"
                :triggers="['hover']"
            >
                <EscrButton
                    aria-label="Reset zoom"
                    color="text"
                    :on-click="onZoomReset"
                    :disabled="disabled"
                >
                    <template #button-icon>
                        <ZoomResetIcon />
                    </template>
                </EscrButton>
                <template #popper>
                    Reset zoom (Ctrl 0)
                </template>
            </VDropdown>
        </div>
    </div>
</template>
<script>
import CursorPanIcon from "../Icons/CursorPanIcon/CursorPanIcon.vue";
import CursorSelectIcon from "../Icons/CursorSelectIcon/CursorSelectIcon.vue";
import EscrButton from "../Button/Button.vue";
import ToggleButton from "../ToggleButton/ToggleButton.vue";
import ZoomInIcon from "../Icons/ZoomInIcon/ZoomInIcon.vue";
import ZoomOutIcon from "../Icons/ZoomOutIcon/ZoomOutIcon.vue";
import ZoomResetIcon from "../Icons/ZoomResetIcon/ZoomResetIcon.vue";
import { Dropdown as VDropdown } from "floating-vue";
import "./EditorGlobalToolbar.css";

export default {
    name: "EscrEditorGlobalToolbar",
    components: {
        CursorPanIcon,
        CursorSelectIcon,
        EscrButton,
        ToggleButton,
        VDropdown,
        ZoomInIcon,
        ZoomOutIcon,
        ZoomResetIcon,
    },
    props: {
        /**
         * True if all buttons and tools should be disabled
         */
        disabled: {
            type: Boolean,
            required: true,
        },
        /**
         * Callback function to zoom in
         */
        onZoomIn: {
            type: Function,
            required: true,
        },
        /**
         * Callback function to zoom out
         */
        onZoomOut: {
            type: Function,
            required: true,
        },
        /**
         * Callback function to reset zoom
         */
        onZoomReset: {
            type: Function,
            required: true,
        },
        /**
         * Callback function to toggle one of the toggleable tools (pan, select)
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
    }
}
</script>
