<template>
    <div
        :class="{ 'escr-toolbar': true, [`escr-${panelType}-toolbar`]: true }"
    >
        <div class="escr-editortools-switcher">
            <VMenu
                placement="bottom-start"
                theme="vertical-menu"
                :distance="8"
                :shown="panelMenuOpen"
                :triggers="[]"
                :auto-hide="true"
                @apply-hide="closePanelMenu"
            >
                <EscrButton
                    :disabled="disabled"
                    :on-click="openPanelMenu"
                    color="text-alt"
                    aria-label="Change Panel"
                >
                    <template #button-icon>
                        <component :is="panelIcon" />
                    </template>
                    <template #button-icon-right>
                        <ChevronDownIcon />
                    </template>
                </EscrButton>
                <template #popper>
                    <ul class="escr-vertical-menu">
                        <li>
                            <button
                                type="button"
                                @mousedown="() => onSwitchPanel({
                                    index: panelIndex, panel: 'segmentation'
                                })"
                            >
                                <SegmentIcon />
                                <span>Segmentation</span>
                            </button>
                        </li>
                        <li>
                            <button
                                type="button"
                                @mousedown="() => onSwitchPanel({
                                    index: panelIndex, panel: 'visualisation'
                                })"
                            >
                                <TranscribeIcon />
                                <span>Transcription</span>
                            </button>
                        </li>
                        <li>
                            <button
                                type="button"
                                @mousedown="() => onSwitchPanel({
                                    index: panelIndex, panel: 'diplomatic'
                                })"
                            >
                                <TextPanelIcon />
                                <span>Text / Line Ordering</span>
                            </button>
                        </li>
                    </ul>
                </template>
            </VMenu>
        </div>
        <slot name="editor-tools-center" />
        <div
            v-if="editorPanels.length > 1 && !disabled"
            class="escr-editortools-close"
        >
            <VDropdown
                class="escr-editortools-close"
                theme="escr-tooltip-small"
                placement="bottom"
                :distance="8"
                :triggers="['hover']"
            >
                <button
                    :aria-label="`Close ${panelName} panel`"
                    type="button"
                    @mousedown="() => removeEditorPanel(panelType)"
                >
                    <RemovePanelIcon />
                </button>
                <template #popper>
                    Close {{ panelName }} panel
                </template>
            </VDropdown>
        </div>
    </div>
</template>
<script>
import ChevronDownIcon from "../Icons/ChevronDownIcon/ChevronDownIcon.vue";
import EscrButton from "../Button/Button.vue";
import RemovePanelIcon from "../Icons/RemovePanelIcon/RemovePanelIcon.vue";
import SegmentIcon from "../Icons/SegmentIcon/SegmentIcon.vue";
import TranscribeIcon from "../Icons/TranscribeIcon/TranscribeIcon.vue";
import TextPanelIcon from "../Icons/TextPanelIcon/TextPanelIcon.vue";
import { Dropdown as VDropdown, Menu as VMenu } from "floating-vue";
import { mapActions, mapState } from "vuex";
import "./EditorToolbar.css";

export default {
    name: "EscrEditorToolbar",
    components: {
        ChevronDownIcon,
        EscrButton,
        RemovePanelIcon,
        SegmentIcon,
        TranscribeIcon,
        TextPanelIcon,
        VDropdown,
        VMenu,
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
         * The index of this panel, to allow swapping panels
         */
        panelIndex: {
            type: Number,
            required: true,
        },
        /**
         * The type of panel this toolbar is for
         */
        panelType: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            panelMenuOpen: false,
        }
    },
    computed: {
        ...mapState({
            editorPanels: (state) => state.document.editorPanels,
        }),
        panelIcon() {
            switch (this.panelType) {
                case "segmentation":
                    return SegmentIcon;
                case "visualisation":
                    return TranscribeIcon;
                case "diplomatic":
                    return TextPanelIcon;
                default:
                    return null;
            }
        },
        panelName() {
            switch (this.panelType) {
                case "segmentation":
                    return "segmentation";
                case "visualisation":
                    return "transcription";
                case "diplomatic":
                    return "text/line ordering";
                default:
                    return null;
            }
        }
    },
    methods: {
        ...mapActions("document", ["removeEditorPanel", "switchEditorPanel"]),
        closePanelMenu() {
            this.panelMenuOpen = false;
        },
        onSwitchPanel({ index, panel }) {
            this.switchEditorPanel({ index, panel });
            this.closePanelMenu();
        },
        openPanelMenu() {
            this.panelMenuOpen = true;
        },
    },
}
</script>
