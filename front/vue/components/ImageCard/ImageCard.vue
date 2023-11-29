<template>
    <li
        :class="{
            ['escr-image-card']: true,
            ['image-selected']: selectedParts.includes(parseInt(part.pk)),
        }"
        dir="ltr"
    >
        <img :src="part.thumbnail">

        <!-- select button -->
        <label
            :for="`select-${part.pk}`"
            class="image-checkbox"
        >
            <input
                :id="`select-${part.pk}`"
                type="checkbox"
                class="sr-only"
                :name="`select-${part.pk}`"
                :checked="selectedParts.includes(parseInt(part.pk))"
                @change="(e) => onToggleSelected(
                    e, parseInt(part.pk), part.order + 1
                )"
                @click="(e) => onClickSelect(e, part.order + 1)"
            >
            <CheckCircleFilledIcon aria-hidden="true" />
            <span aria-hidden="true" />
        </label>

        <!-- edit link and quick actions menu -->
        <div
            :class="{
                'escr-image-actions': true,
                'context-menu-open': contextMenuOpen === true,
            }"
        >
            <VDropdown
                placement="bottom"
                :triggers="['hover']"
                theme="escr-tooltip-small"
            >
                <a
                    :class="{
                        'escr-button': true,
                        'escr-button--secondary': true,
                        'escr-button--small': true,
                        'escr-button--round': true,
                        'escr-button--icon-only': true
                    }"
                    :disabled="loading && loading.images"
                    :href="part.href"
                    aria-label="edit image"
                >
                    <EditImageIcon />
                </a>
                <template #popper>
                    Edit
                </template>
            </VDropdown>
            <VMenu
                placement="bottom-start"
                :triggers="['click']"
                theme="vertical-menu"
                @apply-show="openContextMenu(part.pk)"
                @apply-hide="closeContextMenu()"
            >
                <EscrButton
                    class="context-menu-button"
                    color="secondary"
                    round
                    size="small"
                    :disabled="loading && loading.images"
                    :on-click="() => {}"
                >
                    <template #button-icon>
                        <HorizMenuIcon />
                    </template>
                </EscrButton>
                <template #popper>
                    <ul class="escr-vertical-menu">
                        <li>
                            <button
                                @mousedown="() => selectPartAndOpenModal(part.pk, 'segment')"
                            >
                                <SegmentIcon class="escr-menuitem-icon" />
                                <span>Segment</span>
                            </button>
                        </li>
                        <li>
                            <button
                                @mousedown="() => selectPartAndOpenModal(part.pk, 'transcribe')"
                            >
                                <TranscribeIcon class="escr-menuitem-icon" />
                                <span>Transcribe</span>
                            </button>
                        </li>
                        <li>
                            <button
                                @mousedown="() => selectPartAndOpenModal(part.pk, 'align')"
                            >
                                <AlignIcon class="escr-menuitem-icon" />
                                <span>Align</span>
                            </button>
                        </li>
                        <li>
                            <button
                                @mousedown="() => selectPartAndOpenModal(part.pk, 'export')"
                            >
                                <ExportIcon class="escr-menuitem-icon" />
                                <span>Export</span>
                            </button>
                        </li>
                        <li class="new-section">
                            <button
                                @mousedown="() => openDeleteModal(part)"
                            >
                                <TrashIcon class="escr-menuitem-icon" />
                                <span>Delete</span>
                            </button>
                        </li>
                    </ul>
                </template>
            </VMenu>
        </div>

        <!-- filename with tooltip for overflow -->
        <VDropdown
            placement="bottom"
            :triggers="['hover']"
            theme="escr-tooltip-small"
            class="filename"
        >
            <span>{{ part.title }}</span>
            <template #popper>
                {{ part.title }}
            </template>
        </VDropdown>

        <!-- image task status -->
        <div class="image-status">
            <VDropdown
                placement="bottom"
                :triggers="['hover']"
                theme="escr-task-tooltip"
            >
                <SegmentIcon
                    :class="(part.workflow && part.workflow.segment) || ''"
                />
                <template #popper>
                    <div>
                        <SegmentIcon />
                        <span>Segmentation</span>
                    </div>
                    <div class="task-metadata">
                        <span
                            v-if="part.workflow && part.workflow.segment"
                            :class="{
                                [part.workflow.segment]: true,
                                status: true,
                            }"
                        >
                            {{ part.workflow.segment|workflowString }}
                        </span>
                        <span
                            v-else
                            class="status"
                        >
                            Not initiated
                        </span>
                        <!-- TODO: Uncomment when task date info in API -->
                        <!-- <span class="date">
                            {{ part.segment_date|formatDate }}
                        </span> -->
                    </div>
                </template>
            </VDropdown>
            <VDropdown
                placement="bottom"
                :triggers="['hover']"
                theme="escr-task-tooltip"
            >
                <TranscribeIcon
                    :class="(part.workflow && part.workflow.transcribe) || ''"
                />
                <template #popper>
                    <div>
                        <TranscribeIcon />
                        <span>Transcription</span>
                    </div>
                    <div class="task-metadata">
                        <span
                            v-if="part.workflow && part.workflow.transcribe"
                            :class="{
                                [part.workflow.transcribe]: true,
                                status: true,
                            }"
                        >
                            {{ part.workflow.transcribe|workflowString }}
                        </span>
                        <span
                            v-else
                            class="status"
                        >
                            Not initiated
                        </span>
                        <!-- <span class="date">
                            {{ part.transcribe_date|formatDate }}
                        </span> -->
                    </div>
                </template>
            </VDropdown>
            <VDropdown
                placement="bottom"
                :triggers="['hover']"
                theme="escr-task-tooltip"
            >
                <AlignIcon
                    :class="(part.workflow && part.workflow.align) || ''"
                />
                <template #popper>
                    <div>
                        <AlignIcon />
                        <span>Alignment</span>
                    </div>
                    <div class="task-metadata">
                        <span
                            v-if="part.workflow && part.workflow.align"
                            :class="{
                                [part.workflow.align]: true,
                                status: true,
                            }"
                        >
                            {{ part.workflow.align|workflowString }}
                        </span>
                        <span
                            v-else
                            class="status"
                        >
                            Not initiated
                        </span>
                        <!-- <span class="date">
                            {{ part.align_date|formatDate }}
                        </span> -->
                    </div>
                </template>
            </VDropdown>
        </div>
        <span class="element-number">{{ part.order + 1 }}</span>
    </li>
</template>

<script>
import { mapActions, mapMutations, mapState } from "vuex";
import { Dropdown as VDropdown, Menu as VMenu } from "floating-vue";

import AlignIcon from "../../components/Icons/AlignIcon/AlignIcon.vue";
// eslint-disable-next-line max-len
import CheckCircleFilledIcon from "../../components/Icons/CheckCircleFilledIcon/CheckCircleFilledIcon.vue";
import EditImageIcon from "../../components/Icons/EditImageIcon/EditImageIcon.vue";
import EscrButton from "../../components/Button/Button.vue";
import ExportIcon from "../../components/Icons/ExportIcon/ExportIcon.vue";
import HorizMenuIcon from "../../components/Icons/HorizMenuIcon/HorizMenuIcon.vue";
import SegmentIcon from "../../components/Icons/SegmentIcon/SegmentIcon.vue";
import TranscribeIcon from "../../components/Icons/TranscribeIcon/TranscribeIcon.vue";
import TrashIcon from "../../components/Icons/TrashIcon/TrashIcon.vue";
import "./ImageCard.css";

export default {
    name: "EscrImageCard",
    components: {
        AlignIcon,
        CheckCircleFilledIcon,
        EditImageIcon,
        EscrButton,
        ExportIcon,
        HorizMenuIcon,
        SegmentIcon,
        TranscribeIcon,
        TrashIcon,
        VDropdown,
        VMenu,
    },
    filters: {
        /**
         * Proper formatting for dates
         * TODO: not yet used, awaiting backend support for task dates
         */
        formatDate(date) {
            return new Date(date).toLocaleDateString(
                undefined,
                {
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                    hour: "numeric",
                    minute: "numeric",
                    second: "numeric",
                },
            );
        },
        /**
         * Get the label for a workflow using the internal name as a key
         */
        workflowString(state) {
            switch (state) {
                case "pending":
                    return "Initiated";
                case "ongoing":
                    return "In Progress";
                case "error":
                    return "Error";
                case "done":
                    return "Completed";
                default:
                    return "Not initiated";
            }
        }
    },
    props: {
        /**
         * Callback to close this image's context menu
         */
        closeContextMenu: {
            type: Function,
            required: true,
        },
        /**
         * True if the context menu for this image is open
         */
        contextMenuOpen: {
            type: Boolean,
            required: true,
        },
        /**
         * Callback for clicking the select button for this image
         */
        onClickSelect: {
            type: Function,
            required: true,
        },
        /**
         * Callback for toggling this image's selection state
         */
        onToggleSelected: {
            type: Function,
            required: true,
        },
        /**
         * Callback for opening this image's context menu
         */
        openContextMenu: {
            type: Function,
            required: true,
        },
        /**
         * This image as a JS object
         */
        part: {
            type: Object,
            required: true,
        },
    },
    computed: {
        ...mapState({
            loading: (state) => state.images.loading,
            selectedParts: (state) => state.images.selectedParts,
        })
    },
    methods: {
        ...mapActions("tasks", ["openModal"]),
        ...mapActions("images", ["openDeleteModal"]),
        ...mapMutations("images", ["setSelectedParts"]),
        /**
         * Handler for opening a task modal on one image from context menu
         */
        selectPartAndOpenModal(partPk, modal) {
            this.setSelectedParts([partPk]);
            this.openModal(modal);
        },
    }
}
</script>
