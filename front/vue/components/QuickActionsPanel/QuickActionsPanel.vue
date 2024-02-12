<template>
    <ul class="escr-quick-actions">
        <li>
            <VDropdown
                placement="left"
                :triggers="['hover']"
                theme="tags-dropdown"
            >
                <EscrButton
                    color="text"
                    :disabled="!data || data.disabled"
                    :on-click="() => openModal('import')"
                    label="Import"
                >
                    <template #button-icon>
                        <ImportIcon />
                    </template>
                </EscrButton>
                <template #popper>
                    <span class="escr-tooltip-text">
                        Import images or transcription content.
                    </span>
                </template>
            </VDropdown>
        </li>
        <li>
            <EscrButton
                color="text"
                :disabled="!data || data.disabled"
                :on-click="() => openModal('segment')"
                :label="`Segment ${data && data.scope}`"
            >
                <template #button-icon>
                    <SegmentIcon />
                </template>
            </EscrButton>
        </li>
        <li>
            <EscrButton
                color="text"
                :disabled="!data || data.disabled"
                :on-click="() => openModal('transcribe')"
                :label="`Transcribe ${data && data.scope}`"
            >
                <template #button-icon>
                    <TranscribeIcon />
                </template>
            </EscrButton>
        </li>
        <li>
            <EscrButton
                color="text"
                :disabled="!data || data.disabled"
                :on-click="() => openModal('align')"
                :label="`Align ${data && data.scope}`"
            >
                <template #button-icon>
                    <AlignIcon />
                </template>
            </EscrButton>
        </li>
        <li>
            <EscrButton
                color="text"
                :disabled="!data || data.disabled"
                :on-click="() => openModal('export')"
                :label="`Export ${data && data.scope}`"
            >
                <template #button-icon>
                    <ExportIcon />
                </template>
            </EscrButton>
        </li>
    </ul>
</template>

<script>
import { Dropdown as VDropdown } from "floating-vue";
import { mapActions } from "vuex";
import AlignIcon from "../Icons/AlignIcon/AlignIcon.vue";
import EscrButton from "../Button/Button.vue";
import ExportIcon from "../Icons/ExportIcon/ExportIcon.vue";
import ImportIcon from "../Icons/ImportIcon/ImportIcon.vue";
import SegmentIcon from "../Icons/SegmentIcon/SegmentIcon.vue";
import TranscribeIcon from "../Icons/TranscribeIcon/TranscribeIcon.vue";
import "./QuickActionsPanel.css";

export default {
    name: "EscrQuickActionsPanel",
    components: {
        AlignIcon,
        EscrButton,
        ExportIcon,
        ImportIcon,
        SegmentIcon,
        TranscribeIcon,
        VDropdown,
    },
    props: {
        /**
         * Data for the quick actions panel, an object containing:
         * {
         *     disabled: Boolean, // true if the buttons on the panel should be disabled
         *     scope: String, // indicate if this panel is for "Document" or "Elements"
         * }
         */
        data: {
            type: Object,
            required: true,
        },
    },
    methods: {
        ...mapActions("tasks", [
            "closeModal",
            "openModal",
        ]),
    }
};
</script>
