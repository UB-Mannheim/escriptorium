<template>
    <EscrPage
        class="escr-images-page"
        :breadcrumbs="breadcrumbs"
        :sidebar-actions="sidebarActions"
        :loading="loading && loading.document"
    >
        <template #page-content>
            <div class="escr-container">
                <!-- header with metadata and import button -->
                <div class="escr-images-header">
                    <div class="escr-images-title">
                        <h3 :title="documentName">
                            {{ documentName || "Loading..." }}
                        </h3>
                        <h1>Images</h1>
                    </div>
                    <VDropdown
                        placement="bottom-end"
                        :triggers="['hover']"
                        theme="escr-tooltip-small"
                    >
                        <EscrButton
                            color="primary"
                            :disabled="loading && loading.document"
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
                </div>

                <!-- toolbar with searching, selecting -->
                <div class="escr-images-toolbar">
                    <div class="escr-toolbar-left">
                        <span
                            v-if="!loading.document"
                            class="escr-parts-count"
                        >
                            {{
                                (!loading.document && partsCount)
                                    ? `${partsCount.toLocaleString()} images`
                                    : ''
                            }}
                        </span>
                        <EscrLoader
                            v-else
                            class="escr-parts-count"
                            :loading="loading && loading.document"
                            no-data-message="0 images"
                        />
                        <TextField
                            :disabled="loading && loading.images"
                            :on-input="onSearch"
                            :label-visible="false"
                            :value="textFilter"
                            label="Search to filter images"
                            placeholder="Search"
                        />
                    </div>
                    <div class="escr-toolbar-right">
                        <TextField
                            v-tooltip="{
                                content: rangeValidationError,
                                html: true,
                                shown: !!rangeValidationError,
                                triggers: ['focus'],
                                theme: 'escr-tooltip-small',
                                placement: 'top-end',
                            }"
                            :disabled="loading && loading.images"
                            :on-input="onRangeInput"
                            :invalid="!!rangeValidationError"
                            :label-visible="false"
                            :value="rangeInputValue"
                            class="range-text-field"
                            :label="'Enter multiple numbers separated by a comma, and/or ranges ' +
                                'separated by a dash, to select images'"
                            placeholder="Enter select range"
                        />
                        <EscrButton
                            color="text"
                            label="Select All"
                            size="small"
                            :disabled="(loading && loading.images) || selectedParts.length === parts.length"
                            :on-click="selectAll"
                        />
                        <div class="new-section">
                            <ToggleButton
                                color="secondary"
                                label="Reorder"
                                :checked="isReorderMode"
                                :disabled="loading && loading.images"
                                :on-change="() => isReorderMode = !isReorderMode"
                            >
                                <template #button-icon>
                                    <LineOrderingIcon />
                                </template>
                            </ToggleButton>
                        </div>
                    </div>
                </div>

                <!-- selection toolbar -->
                <div
                    v-if="selectedParts && selectedParts.length > 0"
                    class="escr-image-selection-toolbar"
                >
                    <span class="selected-count">
                        {{ selectedParts.length }} selected
                    </span>
                    <div
                        v-if="isReorderMode"
                        class="escr-toolbar-center"
                    >
                        <EscrButton
                            color="secondary"
                            label="Move to top"
                            size="small"
                            :on-click="() => moveSelectedParts(0)"
                        >
                            <template #button-icon>
                                <MoveToTopIcon />
                            </template>
                        </EscrButton>
                        <EscrButton
                            color="secondary"
                            label="Move to bottom"
                            size="small"
                            :on-click="() => moveSelectedParts(-1)"
                        >
                            <template #button-icon>
                                <MoveToBottomIcon />
                            </template>
                        </EscrButton>
                        <EscrButton
                            color="secondary"
                            label="Move to..."
                            size="small"
                            :on-click="openMoveModal"
                        >
                            <template #button-icon>
                                <MoveImageIcon />
                            </template>
                        </EscrButton>
                    </div>
                    <div
                        v-else
                        class="escr-toolbar-center"
                    >
                        <EscrButton
                            color="secondary"
                            label="Segment"
                            size="small"
                            :disabled="loading && loading.images"
                            :on-click="() => openModal('segment')"
                        >
                            <template #button-icon>
                                <SegmentIcon />
                            </template>
                        </EscrButton>
                        <EscrButton
                            color="secondary"
                            label="Transcribe"
                            size="small"
                            :disabled="loading && loading.images"
                            :on-click="() => openModal('transcribe')"
                        >
                            <template #button-icon>
                                <TranscribeIcon />
                            </template>
                        </EscrButton>
                        <EscrButton
                            color="secondary"
                            label="Align"
                            size="small"
                            :disabled="loading && loading.images"
                            :on-click="() => openModal('align')"
                        >
                            <template #button-icon>
                                <AlignIcon />
                            </template>
                        </EscrButton>
                        <VMenu
                            placement="bottom-start"
                            :triggers="['click']"
                            theme="vertical-menu"
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
                                            @mousedown="() => openModal('export')"
                                        >
                                            <ExportIcon class="escr-menuitem-icon" />
                                            <span>Export</span>
                                        </button>
                                    </li>
                                    <li class="new-section">
                                        <button
                                            @mousedown="() => openDeleteModal()"
                                        >
                                            <TrashIcon class="escr-menuitem-icon" />
                                            <span>Delete</span>
                                        </button>
                                    </li>
                                </ul>
                            </template>
                        </VMenu>
                    </div>
                    <EscrButton
                        color="secondary"
                        label="Clear All"
                        size="small"
                        :disabled="loading && loading.images"
                        :on-click="selectNone"
                    >
                        <template #button-icon>
                            <XCircleFilledIcon />
                        </template>
                    </EscrButton>
                </div>

                <!-- image grid -->
                <div
                    v-if="parts && parts.length"
                    class="escr-image-grid"
                    :dir="readDirection"
                >
                    <ul>
                        <!-- image cards -->
                        <ImageCard
                            v-for="part in filteredParts"
                            :key="part.pk"
                            :part="part"
                            :close-context-menu="closeContextMenu"
                            :open-context-menu="openContextMenu"
                            :context-menu-open="contextMenuOpen === part.pk"
                            :on-toggle-selected="onToggleSelected"
                            :on-click-select="onClickSelect"
                            :is-draggable="isReorderMode"
                        />
                        <li
                            v-if="filteredParts.length < parts.length"
                            class="not-shown"
                            dir="ltr"
                        >
                            <span>
                                {{ parts.length - filteredParts.length }}
                                images hidden by search filter
                            </span>
                            <span
                                v-if="hiddenSelectedCount > 0"
                            >
                                including {{ hiddenSelectedCount }} selected images
                            </span>
                            <EscrButton
                                label="Clear search filter"
                                color="outline-secondary"
                                size="small"
                                :disabled="loading && loading.images"
                                :on-click="() => textFilter = ''"
                            >
                                <template #button-icon>
                                    <XCircleFilledIcon />
                                </template>
                            </EscrButton>
                        </li>
                    </ul>
                    <EscrButton
                        v-if="nextPage"
                        label="Load more"
                        class="escr-load-more-btn"
                        color="outline-primary"
                        size="small"
                        :disabled="loading && loading.images"
                        :on-click="async () => await fetchNextPage()"
                    />
                    <div
                        v-if="loading && loading.images"
                        class="images-loading-overlay"
                    />
                </div>
                <EscrLoader
                    v-else
                    class="grid-spinner"
                    :loading="loading && loading.images"
                    no-data-message="There are no images to display."
                />

                <!-- import images modal -->
                <ImportModal
                    v-if="taskModalOpen && taskModalOpen.import"
                    :disabled="loading && loading.document"
                    :on-cancel="() => closeTaskModal('import')"
                    :on-submit="onSubmitImport"
                />
                <!-- cancel image uploads modal -->
                <ConfirmModal
                    v-if="taskModalOpen && taskModalOpen.imageCancelWarning"
                    :body-text="'Uploads are still in progress. Are you sure you want ' +
                        'to cancel? Incomplete uploads may be lost.'"
                    title="Cancel Upload In Progress"
                    cancel-verb="No"
                    confirm-verb="Yes, cancel"
                    :disabled="loading && (loading.images || loading.document)"
                    :on-cancel="() => closeTaskModal('imageCancelWarning')"
                    :on-confirm="confirmImageCancelWarning"
                    :cannot-undo="false"
                />

                <!-- move images modal -->
                <MoveImagesModal
                    v-if="moveModalOpen"
                    :disabled="loading && loading.images"
                    :on-cancel="onCancelMove"
                    :on-submit="onSubmitMove"
                />

                <!-- segment images modal -->
                <SegmentModal
                    v-if="taskModalOpen && taskModalOpen.segment"
                    :models="segmentationModels"
                    :disabled="loading && (loading.images || loading.document)"
                    :on-cancel="() => {
                        closeTaskModal('segment');
                        if (selectedParts.length === 1) setSelectedParts([]);
                    }"
                    :on-submit="handleSubmitSegmentation"
                    :scope="selectedParts.length === 1 ? 'Image' : `${selectedParts.length} Images`"
                />
                <!-- transcribe images modal -->
                <TranscribeModal
                    v-if="taskModalOpen && taskModalOpen.transcribe"
                    :models="recognitionModels"
                    :disabled="loading && (loading.images || loading.document)"
                    :on-cancel="() => {
                        closeTaskModal('transcribe');
                        if (selectedParts.length === 1) setSelectedParts([]);
                    }"
                    :on-submit="handleSubmitTranscribe"
                    :scope="selectedParts.length === 1 ? 'Image' : `${selectedParts.length} Images`"
                />
                <!-- overwrite segmentation modal -->
                <ConfirmModal
                    v-if="taskModalOpen && taskModalOpen.overwriteWarning"
                    :body-text="'Are you sure you want to continue? Re-segmenting will delete ' +
                        'any existing transcriptions.'"
                    title="Overwrite Existing Segmentation and Transcriptions"
                    confirm-verb="Continue"
                    :disabled="loading && (loading.images || loading.document)"
                    :cannot-undo="true"
                    :on-cancel="() => closeTaskModal('overwriteWarning')"
                    :on-confirm="confirmOverwriteWarning"
                />
                <!-- align images modal -->
                <AlignModal
                    v-if="taskModalOpen && taskModalOpen.align"
                    :transcriptions="transcriptions"
                    :region-types="regionTypes"
                    :disabled="loading && (loading.images || loading.document)"
                    :on-cancel="() => {
                        closeTaskModal('align');
                        if (selectedParts.length === 1) setSelectedParts([]);
                    }"
                    :on-submit="handleSubmitAlign"
                    :textual-witnesses="textualWitnesses"
                    :scope="selectedParts.length === 1 ? 'Image' : `${selectedParts.length} Images`"
                />
                <!-- export images modal -->
                <ExportModal
                    v-if="taskModalOpen && taskModalOpen.export"
                    :markdown-enabled="markdownEnabled"
                    :tei-enabled="teiEnabled"
                    :transcriptions="transcriptions"
                    :region-types="regionTypes"
                    :disabled="loading && (loading.images || loading.document)"
                    :on-cancel="() => {
                        closeTaskModal('export');
                        if (selectedParts.length === 1) setSelectedParts([]);
                    }"
                    :on-submit="handleSubmitExport"
                    :scope="selectedParts.length === 1 ? 'Image' : `${selectedParts.length} Images`"
                />
                <!-- delete images modal -->
                <ConfirmModal
                    v-if="deleteModalOpen"
                    :body-text="partTitleToDelete ?
                        `Are you sure you want to delete ${partTitleToDelete}?` :
                        'Are you sure you want to delete the selected image(s)?'"
                    confirm-verb="Delete"
                    :title="selectedParts.length === 1 ? 'Delete Image' : 'Delete Images'"
                    :cannot-undo="true"
                    :disabled="loading && loading.images"
                    :on-cancel="() => closeDeleteModal(!!partTitleToDelete)"
                    :on-confirm="deleteSelectedParts"
                />
            </div>
        </template>
    </EscrPage>
</template>
<script>
import { Dropdown as VDropdown, Menu as VMenu } from "floating-vue";
import { range } from "lodash";
import ReconnectingWebSocket from "reconnectingwebsocket";
import { mapActions, mapMutations, mapState } from "vuex";

import AlignIcon from "../../components/Icons/AlignIcon/AlignIcon.vue";
import AlignModal from "../../components/AlignModal/AlignModal.vue";
import ConfirmModal from "../../components/ConfirmModal/ConfirmModal.vue";
import EscrButton from "../../components/Button/Button.vue";
import EscrLoader from "../../components/Loader/Loader.vue";
import EscrPage from "../Page/Page.vue";
import ExportIcon from "../../components/Icons/ExportIcon/ExportIcon.vue";
import ExportModal from "../../components/ExportModal/ExportModal.vue";
import HorizMenuIcon from "../../components/Icons/HorizMenuIcon/HorizMenuIcon.vue";
import ImageCard from "../../components/ImageCard/ImageCard.vue";
import ImportIcon from "../../components/Icons/ImportIcon/ImportIcon.vue";
import ImportModal from "../../components/ImportModal/ImportModal.vue";
import LineOrderingIcon from "../../components/Icons/LineOrderingIcon/LineOrderingIcon.vue";
import ModelsIcon from "../../components/Icons/ModelsIcon/ModelsIcon.vue";
import ModelsPanel from "../../components/ModelsPanel/ModelsPanel.vue";
import MoveImageIcon from "../../components/Icons/MoveImageIcon/MoveImageIcon.vue";
import MoveImagesModal from "../../components/MoveImagesModal/MoveImagesModal.vue";
import MoveToBottomIcon from "../../components/Icons/MoveToBottomIcon/MoveToBottomIcon.vue";
import MoveToTopIcon from "../../components/Icons/MoveToTopIcon/MoveToTopIcon.vue";
import PeopleIcon from "../../components/Icons/PeopleIcon/PeopleIcon.vue";
import SearchIcon from "../../components/Icons/SearchIcon/SearchIcon.vue";
import SearchPanel from "../../components/SearchPanel/SearchPanel.vue";
import SegmentIcon from "../../components/Icons/SegmentIcon/SegmentIcon.vue";
import SegmentModal from "../../components/SegmentModal/SegmentModal.vue";
import SharePanel from "../../components/SharePanel/SharePanel.vue";
import TextField from "../../components/TextField/TextField.vue";
import ToggleButton from "../../components/ToggleButton/ToggleButton.vue";
import TranscribeIcon from "../../components/Icons/TranscribeIcon/TranscribeIcon.vue";
import TranscribeModal from "../../components/TranscribeModal/TranscribeModal.vue";
import TrashIcon from "../../components/Icons/TrashIcon/TrashIcon.vue";
import XCircleFilledIcon from "../../components/Icons/XCircleFilledIcon/XCircleFilledIcon.vue";
import "../../components/VerticalMenu/VerticalMenu.css";
import "./Images.css";

export default {
    name: "EscrImages",
    components: {
        AlignIcon,
        AlignModal,
        ConfirmModal,
        EscrButton,
        EscrLoader,
        EscrPage,
        ExportIcon,
        ExportModal,
        HorizMenuIcon,
        ImageCard,
        ImportIcon,
        ImportModal,
        LineOrderingIcon,
        // eslint-disable-next-line vue/no-unused-components
        ModelsIcon,
        // eslint-disable-next-line vue/no-unused-components
        ModelsPanel,
        MoveImageIcon,
        MoveImagesModal,
        MoveToBottomIcon,
        MoveToTopIcon,
        // eslint-disable-next-line vue/no-unused-components
        PeopleIcon,
        // eslint-disable-next-line vue/no-unused-components
        SearchIcon,
        // eslint-disable-next-line vue/no-unused-components
        SearchPanel,
        SegmentIcon,
        SegmentModal,
        // eslint-disable-next-line vue/no-unused-components
        SharePanel,
        TextField,
        ToggleButton,
        TranscribeIcon,
        TranscribeModal,
        TrashIcon,
        VDropdown,
        VMenu,
        XCircleFilledIcon,
    },
    props: {
        /**
         * The primary key/id of the current document.
         */
        id: {
            type: Number,
            required: true,
        },
        /**
         * Whether or not OpenITI Markdown export is enabled on the current instance.
         */
        markdownEnabled: {
            type: Boolean,
            required: true,
        },
        /**
         * Whether or not OpenITI TEI XML export is enabled on the current instance.
         */
        teiEnabled: {
            type: Boolean,
            required: true,
        },
        /**
         * Whether or not search is disabled on the current instance.
         */
        searchDisabled: {
            type: Boolean,
            required: true,
        },
    },
    data() {
        return {
            contextMenuOpen: null,
            isReorderMode: false,
            lastSelected: null,
            rangeValidationError: null,
            rangeInputValue: "",
            rangeRegex: /^\d+((,|-)\d+)*$/g,
            textFilter: "",
        }
    },
    computed: {
        ...mapState({
            deleteModalOpen: (state) => state.images.deleteModalOpen,
            documentName: (state) => state.document.name,
            loading: (state) => state.images.loading,
            models: (state) => state.document.models,
            moveModalOpen: (state) => state.images.moveModalOpen,
            nextPage: (state) => state.images.nextPage,
            partTitleToDelete: (state) => state.images.partTitleToDelete,
            parts: (state) => state.document.parts,
            partsCount: (state) => state.document.partsCount,
            projectId: (state) => state.project.id,
            projectName: (state) => state.document.projectName,
            projectSlug: (state) => state.document.projectSlug,
            readDirection: (state) => state.document.readDirection,
            recognitionModels: (state) => state.user.recognitionModels,
            regionTypes: (state) => state.document.regionTypes,
            segmentationModels: (state) => state.user.segmentationModels,
            selectedParts: (state) => state.images.selectedParts,
            taskModalOpen: (state) => state.tasks.modalOpen,
            textualWitnesses: (state) => state.document.textualWitnesses,
            transcriptions: (state) => state.document.transcriptions,
        }),
        /**
         * Links and titles for the breadcrumbs above the page.
         */
        breadcrumbs() {
            let docBreadcrumbs = [{ title: "Loading..." }, { title: "Loading..." }];
            if (this.projectName && this.projectSlug && this.documentName) {
                docBreadcrumbs = [
                    {
                        title: this.projectName,
                        href: `/project/${this.projectSlug}/`
                    },
                    {
                        title: this.documentName,
                        href: `/document/${this.id}/`
                    },
                ];
            }
            return [
                { title: "My Projects", href: "/projects/" },
                ...docBreadcrumbs,
                { title: "Images" },
            ];
        },
        /**
         * Parts (title) filtered by search query
         */
        filteredParts() {
            if (this.textFilter) {
                return this.sortedParts.filter((part) => {
                    return part.title.toLowerCase().includes(this.textFilter.toLowerCase());
                });
            }
            else {
                return this.sortedParts;
            }
        },
        /**
         * Parts sorted by order
         */
        sortedParts() {
            return this.parts.toSorted((a, b) => a.order - b.order);
        },
        /**
         * Sidebar quick actions for the document dashboard.
         */
        sidebarActions() {
            let actions = [
                {
                    data: {
                        disabled: this.loading?.document,
                        users: this.sharedWithUsers,
                        groups: this.sharedWithGroups,
                        openShareModal: this.openShareModal,
                    },
                    icon: PeopleIcon,
                    key: "share",
                    label: "Groups & Users",
                    panel: SharePanel,
                },
                {
                    data: {
                        loading: this.loading?.document || this.loading?.models,
                        models: this.models,
                    },
                    icon: ModelsIcon,
                    key: "models",
                    label: "Models",
                    panel: ModelsPanel,
                }
            ];
            // if search is enabled on the instance, add search as first item
            if (!this.searchDisabled) {
                actions.unshift({
                    data: {
                        disabled: this.loading?.document,
                        searchScope: "Document",
                        projectId: this.projectId,
                        documentId: this.id,
                    },
                    icon: SearchIcon,
                    key: "search",
                    label: "Search Document",
                    panel: SearchPanel,
                });
            }
            return actions
        },
        /**
         * number of items selected but filtered out
         */
        hiddenSelectedCount() {
            return this.selectedParts.filter(
                (pk) => !this.filteredParts.map((part) => part.pk).includes(pk)
            ).length;
        },
    },
    /**
     * On load, fetch basic details about the document.
     */
    async created() {
        this.setId(this.id);
        // join document websocket room
        const msg = `{"type": "join-room", "object_cls": "document", "object_pk": ${this.id}}`;
        const scheme = location.protocol === "https:" ? "wss:" : "ws:";
        const msgSocket = new ReconnectingWebSocket(`${scheme}//${window.location.host}/ws/notif/`);
        msgSocket.maxReconnectAttempts = 3;
        msgSocket.addEventListener("open", function() {
            msgSocket.send(msg);
        });
        // handle document-related websocket events
        msgSocket.addEventListener("message", this.websocketTaskListener);
        // load document
        try {
            await this.fetchDocument();
            this.setLoading({ key: "document", loading: false });
        } catch (error) {
            this.setLoading({ key: "document", loading: false });
            this.addError(error);
        }
        // load models
        try {
            await this.fetchDocumentModels();
            await this.fetchSegmentModels();
            await this.fetchRecognizeModels();
            this.setLoading({ key: "models", loading: false });
        } catch(error) {
            this.setLoading({ key: "models", loading: false });
            this.addError(error);
        }
        // load groups and users
        try {
            await this.fetchGroups();
            this.setLoading({ key: "groups", loading: false });
        } catch(error) {
            this.setLoading({ key: "groups", loading: false });
            this.addError(error);
        }
    },
    methods: {
        ...mapActions("alerts", ["addError"]),
        ...mapActions("document", [
            "confirmImageCancelWarning",
            "fetchDocumentModels",
            "handleSubmitImport",
            "setId",
        ]),
        ...mapActions("images", [
            "confirmOverwriteWarning",
            "closeDeleteModal",
            "deleteSelectedParts",
            "fetchDocument",
            "fetchNextPage",
            "handleSubmitAlign",
            "handleSubmitExport",
            "handleSubmitSegmentation",
            "handleSubmitTranscribe",
            "moveSelectedParts",
            "onCancelMove",
            "onSubmitMove",
            "openDeleteModal",
            "openMoveModal",
            "setSelectedPartsByOrder",
            "togglePartSelected",
        ]),
        ...mapActions("tasks", {
            align: "alignImages",
            cancelTask: "cancel",
            closeTaskModal: "closeModal",
            export: "exportImages",
            openModal: "openModal",
            transcribe: "transcribeImages",
        }),
        ...mapActions("user", ["fetchGroups", "fetchRecognizeModels", "fetchSegmentModels"]),
        ...mapMutations("images", ["setLoading", "setSelectedParts"]),
        /**
         * Close a context menu for an image.
         */
        closeContextMenu() {
            this.contextMenuOpen = null;
        },
        /**
         * Handle range input, validate, and set selected parts if valid
         */
        async onRangeInput(e) {
            this.rangeInputValue = e.target.value;
            // collect selected indices and validate for errors
            const { selected, error } = this.validateSelectRange(
                // be lenient with spaces
                this.rangeInputValue.replace(" ", "")
            );
            this.rangeValidationError = error;
            if (!error) {
                // set selected items on state
                while (selected.length > this.parts.length && this.nextPage) {
                    await this.fetchNextPage();
                }
                this.setSelectedPartsByOrder(selected);
            }
        },
        /**
         * Handle search to filter
         */
        onSearch(e) {
            this.textFilter = e.target.value;
        },
        /**
         * Handle the checkbox input to select/deselect parts
         */
        onToggleSelected(e, partPk, order) {
            this.togglePartSelected(partPk);
            if (e.target.checked && !this.lastSelected) {
                // save the last selected item (for multiple selection with shift key)
                this.lastSelected = order;
            } else if (!e.target.checked) {
                // clear last selected
                this.lastSelected = null;
            }
        },
        /**
         * Handle multiple selection with shift key
         */
        onClickSelect(e, clicked) {
            if (
                e.target.checked &&
                e.shiftKey &&
                this.lastSelected &&
                this.lastSelected !== clicked
            ) {
                // generate range based on whether beginning or end of selection is larger
                if (clicked < this.lastSelected) {
                    // exclude clicked item itself from range; handled in onToggleSelected!
                    this.setSelectedPartsByOrder([...range(clicked + 1, this.lastSelected + 1)]);
                } else {
                    this.setSelectedPartsByOrder([...range(this.lastSelected, clicked)]);
                }
            }
        },
        /**
         * Set loading state on, run the document module's import code, set loading off
         */
        async onSubmitImport() {
            this.setLoading({ key: "document", loading: true });
            await this.handleSubmitImport();
            this.setLoading({ key: "document", loading: false });
        },
        /**
         * Open a context menu for an image by pk.
         */
        openContextMenu(pk) {
            this.contextMenuOpen = pk;
        },
        /**
         * Handler for clicking "select all"
         */
        async selectAll() {
            this.setLoading({ key: "images", loading: true });
            while (this.nextPage) {
                await this.fetchNextPage();
            }
            this.setLoading({ key: "images", loading: false });
            this.setSelectedParts(this.parts.map((part) => part.pk));
        },
        /**
         * Handler for clicking "select none"
         */
        selectNone() {
            this.setSelectedParts([]);
        },
        /**
         * Validate the passed range string:
         *   - must be only numbers, dashes, and commas
         *   - must be a valid range of less than 5000 numbers
         */
        validateSelectRange(val) {
            let validationError = null;
            const selected = [];
            if (val.match(this.rangeRegex)) {
                // maybe valid if matching regex
                // split out comma separated numbers and ranges (e.g. "3,4-30,31")
                const commaSeparated = val.split(",");
                commaSeparated.forEach((str) => {
                    // find ranges and validate them
                    const dashSeparated = str.split("-");
                    if (dashSeparated.length > 2) {
                        // multiple dashes e.g. 1-100-150 is invalid
                        validationError = "Invalid range; dashes may only separate two numbers";
                    } else if (dashSeparated.length === 2) {
                        // validate for actual range
                        const leftVal = parseInt(dashSeparated[0]);
                        const rightVal = parseInt(dashSeparated[1]);
                        if (leftVal >= rightVal) {
                            validationError = "Invalid range; first number must be smaller than " +
                                "second";
                        } else if (rightVal - leftVal >= 5000) {
                            // validate for limit (memory constraint on the range() function)
                            validationError = "Range exceeded maximum number of selections (5000)";
                        } else {
                            // select all numbers in the range
                            selected.push(...range(leftVal, rightVal + 1));
                        }
                    } else {
                        // not a range, just one number, so it's valid
                        selected.push(parseInt(dashSeparated[0]));
                    }
                });
            } else if (val) {
                // invalid if not matching regex (unless empty)
                validationError = "Must be a list of numbers separated by commas, and/or numeric " +
                    "ranges separated by dashes";
            }
            // get unique selected indices and unique errors
            return {
                selected: [...new Set(selected)],
                error: validationError,
            };
        },
        async websocketTaskListener(e) {
            const data = JSON.parse(e.data);
            // handle task-related events
            const taskEvents = [
                "export:", "import:", "part:mask", "part:workflow", "training:"
            ];
            if (
                data.type === "event" && taskEvents.some((task) => data.name.startsWith(task))
            ) {
                // TODO: how to handle? we need image part statuses to update
                // these may be frequent, so throttle
            }
        },
    },
}
</script>
