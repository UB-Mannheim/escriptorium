<template>
    <li class="escr-card-container">
        <div
            :class="{
                ['escr-part-dropzone-before']: true,
                ['is-dragging']: isDragging,
                ['drag-over']: dragOver === -1,
            }"
            @dragover="(e) => handleDragOver(e, -1)"
            @dragenter="(e) => e.preventDefault()"
            @dragleave="() => setDragOver(0)"
            @drop="(e) => handleDrop(e, -1)"
        />
        <div
            :class="{
                ['escr-image-card']: true,
                ['image-selected']: selectedParts.includes(parseInt(part.pk)),
            }"
            :draggable="isBeingDragged"
            dir="ltr"
            @dragstart="handleDragStart"
            @dragend="handleDragEnd"
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

            <!-- drag handle -->
            <div
                v-if="isDraggable"
                class="escr-drag-handle"
                @mousedown="handleDragMousedown"
                @mouseup="handleDragEnd"
            >
                <DragHandleIcon />
            </div>

            <!-- edit link and quick actions menu -->
            <div
                v-else
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
        </div>
        <div
            :class="{
                ['escr-part-dropzone-after']: true,
                ['is-dragging']: isDragging,
                ['drag-over']: dragOver === 1,
            }"
            @dragover="(e) => handleDragOver(e, 1)"
            @dragenter="(e) => e.preventDefault()"
            @dragleave="() => setDragOver(0)"
            @drop="(e) => handleDrop(e, 1)"
        />
    </li>
</template>

<script>
import { mapActions, mapMutations, mapState } from "vuex";
import { Dropdown as VDropdown, Menu as VMenu } from "floating-vue";

import AlignIcon from "../../components/Icons/AlignIcon/AlignIcon.vue";
// eslint-disable-next-line max-len
import CheckCircleFilledIcon from "../../components/Icons/CheckCircleFilledIcon/CheckCircleFilledIcon.vue";
import DragHandleIcon from "../../components/Icons/DragHandleIcon/DragHandleIcon.vue";
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
        DragHandleIcon,
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
         * True if the item is draggable
         */
        isDraggable: {
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
    data() {
        return {
            dragOver: 0,
            isBeingDragged: false,
        }
    },
    computed: {
        ...mapState({
            loading: (state) => state.images.loading,
            selectedParts: (state) => state.images.selectedParts,
            isDragging: (state) => state.images.isDragging,
        })
    },
    methods: {
        ...mapActions("alerts", ["addError"]),
        ...mapActions("tasks", ["openModal"]),
        ...mapActions("images", ["movePart", "moveSelectedParts", "openDeleteModal"]),
        ...mapMutations("images", ["setSelectedParts", "setIsDragging"]),
        /**
         * Handler for opening a task modal on one image from context menu
         */
        selectPartAndOpenModal(partPk, modal) {
            this.setSelectedParts([partPk]);
            this.openModal(modal);
        },
        /**
         * Tell this component that it is not being dragged; tell state that dragging has stopped
         */
        handleDragEnd() {
            this.isBeingDragged = false;
            // clean up drag image if present (which has to be added to DOM, unfortunately!)
            const dragImage = document.getElementById("is-drag-image");
            if (dragImage) {
                document.body.removeChild(dragImage);
            }
            // timeout hack to prevent z-fighting with drag handle
            setTimeout(() => {
                this.setIsDragging(false);
            }, 100);
        },
        /**
         * Tell this component that it is being dragged; tell state that dragging has started
         */
        handleDragMousedown() {
            this.isBeingDragged = true;
            // timeout hack to prevent z-fighting with drag handle
            setTimeout(() => {
                this.setIsDragging(true);
            }, 100);
        },
        /**
         * On drag, set this part's pk on the event data so that it can be retrieved on drop.
         * Also, if more than one element is selected, and this is one of the selected elements,
         * show the number of selected elements on drag.
         */
        handleDragStart(e) {
            if(this.isBeingDragged) {
                e.dataTransfer.setData("draggingPk", this.part.pk);
                e.dataTransfer.setData("draggingOrder", this.part.order);
                // a bit of DOM manipulation to show # of selected elements being moved
                if (this.selectedParts.length > 1 && this.selectedParts.includes(this.part.pk)) {
                    // create a copy of this node
                    const clonedNode = e.target.parentNode.cloneNode(true);
                    clonedNode.id = "is-drag-image";
                    // add the elements label
                    const elementsLabel = document.createElement("div");
                    elementsLabel.innerText = `${this.selectedParts.length} elements`;
                    elementsLabel.classList.add("elements-count");
                    clonedNode.prepend(elementsLabel);
                    // append the cloned node to the DOM (it will be positioned offscreen)
                    document.body.appendChild(clonedNode);
                    // use it as the drag image
                    e.dataTransfer.setDragImage(clonedNode, clonedNode.clientWidth / 2, 40);
                }
            }
        },
        /**
         * Set the component state to indicate whether the "after" drop zone is being dragged
         * over (1), the "before" drop zone is (-1), or neither is (0)
         */
        setDragOver(idx) {
            this.dragOver = idx;
        },
        /**
         * When one of this part's drop zones are dragged over, tell component whether it is
         * before (-1) or after (1) this part; also, set the drop effect on the event
         */
        handleDragOver(e, idx) {
            e.preventDefault();
            this.setDragOver(idx);
            e.dataTransfer.dropEffect = "move";
        },
        /**
         * On drop, perform the reordering operation, then turn off all drag-related
         * component and store states.
         */
        async handleDrop(e, idx) {
            const draggingPk = parseInt(e.dataTransfer.getData("draggingPk"));
            const oldIndex = parseInt(e.dataTransfer.getData("draggingOrder"));
            // determine the index to move to
            let newIndex = idx === -1 ? this.part.order : this.part.order + 1;
            if (this.selectedParts.length <= 1 && oldIndex < newIndex) {
                newIndex--;
            }
            if (this.selectedParts.length > 1 && this.selectedParts.includes(draggingPk)) {
                await this.moveSelectedParts({ index: newIndex });
            } else if (draggingPk !== this.part.pk && oldIndex !== newIndex) {
                // if not moving, don't bother making the API request
                await this.movePart({ partPk: draggingPk, index: newIndex });
            }

            this.isBeingDragged = false;
            this.dragOver = 0;
            // timeout hack to prevent z-fighting with drag handle
            setTimeout(() => {
                this.setIsDragging(false);
            }, 100);
        }
    }
}
</script>
