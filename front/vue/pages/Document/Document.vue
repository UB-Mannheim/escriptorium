<template>
    <EscrPage
        class="escr-document-dashboard"
        :breadcrumbs="breadcrumbs"
        :sidebar-actions="sidebarActions"
        :loading="loading && loading.document"
    >
        <template #page-content>
            <div class="escr-grid-container">
                <div class="escr-doc-left-grid">
                    <!-- Document metadata header -->
                    <div class="escr-card escr-card-padding escr-document-details">
                        <div class="escr-card-header">
                            <h1 :title="documentName">
                                {{ documentName }}
                            </h1>
                            <div class="escr-card-actions">
                                <VerticalMenu
                                    :is-open="documentMenuOpen"
                                    :close-menu="closeDocumentMenu"
                                    :open-menu="openDocumentMenu"
                                    :disabled="(loading && loading.document) || editModalOpen || deleteModalOpen"
                                    :items="documentMenuItems"
                                />
                                <EditDocumentModal
                                    v-if="editModalOpen"
                                    :disabled="loading && loading.document"
                                    :new-document="false"
                                    :on-cancel="closeEditModal"
                                    :on-create-tag="createNewDocumentTag"
                                    :on-save="saveDocument"
                                    :scripts="scripts"
                                    :tags="allDocumentTags"
                                />
                            </div>
                        </div>
                        <span class="escr-document-metadata">
                            Main script: {{ mainScript }}
                        </span>
                    </div>

                    <!-- Document tags card -->
                    <div class="escr-card escr-card-padding escr-document-tags">
                        <div class="escr-card-header">
                            <h2>Tags</h2>
                        </div>
                        <EscrTags
                            v-if="tags"
                            :tags="tags"
                            wrap
                        />
                    </div>

                    <!-- Document tasks card -->
                    <div class="escr-card escr-card-table escr-document-tasks">
                        <div class="escr-card-header">
                            <h2>Tasks</h2>
                            <div class="escr-card-actions">
                                <EscrButton
                                    label="View All"
                                    size="small"
                                    :on-click="() => navigateToTasks()"
                                    :disabled="loading && loading.tasks"
                                >
                                    <template #button-icon-right>
                                        <ArrowRightIcon />
                                    </template>
                                </EscrButton>
                            </div>
                        </div>
                        <div class="tasks-container">
                            <TaskDashboard />
                        </div>
                    </div>

                    <!-- Document images list -->
                    <div class="escr-card escr-card-table escr-document-images">
                        <div class="escr-card-header">
                            <h2>Your Recent Images</h2>
                            <div class="escr-card-actions">
                                <EscrButton
                                    label="View All"
                                    size="small"
                                    :on-click="() => navigateToImages()"
                                    :disabled="loading && loading.parts"
                                >
                                    <template #button-icon-right>
                                        <ArrowRightIcon />
                                    </template>
                                </EscrButton>
                            </div>
                        </div>
                        <div class="table-container">
                            <EscrTable
                                :items="parts"
                                :headers="partsHeaders"
                                item-key="pk"
                            />
                        </div>
                    </div>
                </div>
                <div class="escr-doc-right-grid">
                    <!-- transcription picker -->
                    <div class="doc-stats-header">
                        <h2>Document Statistics</h2>
                        <div>
                            <h3>View:</h3>
                            <EscrDropdown
                                :disabled="loading && loading.transcriptions"
                                :options="transcriptionLevels"
                                :on-change="selectTranscription"
                            />
                        </div>
                    </div>

                    <!-- Document total images card -->
                    <div class="escr-card escr-card-padding images-stats">
                        <div class="escr-card-header">
                            <h2>Total Images</h2>
                        </div>
                        <span class="escr-stat">
                            {{
                                (!loading.document && partsCount)
                                    ? partsCount.toLocaleString()
                                    : "-"
                            }}
                        </span>
                    </div>
                    <!-- Document total lines card -->
                    <div class="escr-card escr-card-padding lines-stats">
                        <div class="escr-card-header">
                            <h2>Total Lines</h2>
                        </div>
                        <span class="escr-stat">
                            {{
                                (!loading.transcriptions && lineCount)
                                    ? lineCount.toLocaleString()
                                    : "-"
                            }}
                        </span>
                    </div>
                    <!-- Document total characters card -->
                    <div class="escr-card escr-card-padding chars-stats">
                        <div class="escr-card-header">
                            <h2>Total Characters</h2>
                        </div>
                        <span class="escr-stat">
                            {{
                                (!transcriptionLoading.characterCount && charCount)
                                    ? charCount.toLocaleString()
                                    : "-"
                            }}
                        </span>
                    </div>
                    <!-- Document transcription status card -->
                    <div class="escr-card escr-card-padding transcription-status">
                        <h2>Transcription Status</h2>
                        <dl>
                            <dt>Confidence</dt>
                            <dd>{{ transcriptionConfidence }}</dd>
                        </dl>
                    </div>
                    <!-- Ontology section -->
                    <OntologyCard
                        class="escr-project-ontology"
                        context="Document"
                        compact
                        :items="ontology"
                        :loading="ontologyLoading"
                        :on-view="() => openOntologyModal"
                        :on-select-category="changeOntologyCategory"
                        :on-sort="sortOntology"
                        :selected-category="ontologyCategory"
                    />
                    <!-- Characters section -->
                    <CharactersCard
                        class="escr-project-characters"
                        compact
                        :loading="charactersLoading"
                        :on-view="() => openCharactersModal"
                        :on-sort-characters="sortCharacters"
                        :sort="charactersSort && charactersSort.field"
                        :items="characters"
                    />
                </div>
                <!-- delete document modal -->
                <ConfirmModal
                    v-if="deleteModalOpen"
                    body-text="Are you sure you want to delete this document?"
                    confirm-verb="Delete"
                    title="Delete Document"
                    :cannot-undo="true"
                    :disabled="loading && loading.document"
                    :on-cancel="closeDeleteModal"
                    :on-confirm="deleteDocument"
                />
                <!-- share document modal -->
                <ShareModal
                    v-if="shareModalOpen"
                    :groups="groups"
                    :disabled="loading && (loading.document || loading.user)"
                    :on-cancel="closeShareModal"
                    :on-submit="shareDocument"
                />
                <!-- import images modal -->
                <ImportModal
                    v-if="taskModalOpen && taskModalOpen.import"
                    :disabled="loading && loading.document"
                    :on-cancel="() => closeTaskModal('import')"
                    :on-submit="handleSubmitImport"
                />
                <!-- segment document modal -->
                <SegmentModal
                    v-if="taskModalOpen && taskModalOpen.segment"
                    :models="segmentationModels"
                    :disabled="loading && loading.document"
                    :on-cancel="() => closeTaskModal('segment')"
                    :on-submit="handleSubmitSegmentation"
                    scope="Document"
                />
                <!-- transcribe document modal -->
                <TranscribeModal
                    v-if="taskModalOpen && taskModalOpen.transcribe"
                    :models="recognitionModels"
                    :disabled="loading && loading.document"
                    :on-cancel="() => closeTaskModal('transcribe')"
                    :on-submit="handleSubmitTranscribe"
                    scope="Document"
                />
                <!-- overwrite segmentation modal -->
                <ConfirmModal
                    v-if="taskModalOpen && taskModalOpen.overwriteWarning"
                    :body-text="'Are you sure you want to continue? Re-segmenting will delete ' +
                        'any existing transcriptions.'"
                    title="Overwrite Existing Segmentation and Transcriptions"
                    confirm-verb="Continue"
                    :cannot-undo="true"
                    :on-cancel="() => closeTaskModal('overwriteWarning')"
                    :on-confirm="confirmOverwriteWarning"
                />
                <!-- align document modal -->
                <AlignModal
                    v-if="taskModalOpen && taskModalOpen.align"
                    :transcriptions="transcriptions"
                    :region-types="regionTypes"
                    :disabled="loading && loading.document"
                    :on-cancel="() => closeTaskModal('align')"
                    :on-submit="handleSubmitAlign"
                    :textual-witnesses="textualWitnesses"
                    scope="Document"
                />
                <!-- export document modal -->
                <ExportModal
                    v-if="taskModalOpen && taskModalOpen.export"
                    :transcriptions="transcriptions"
                    :region-types="regionTypes"
                    :disabled="loading && loading.document"
                    :on-cancel="() => closeTaskModal('export')"
                    :on-submit="handleSubmitExport"
                    scope="Document"
                />
                <!-- cancel task modal -->
                <ConfirmModal
                    v-if="taskModalOpen && taskModalOpen.cancelWarning"
                    :body-text="'Are you sure you want to cancel this task?'"
                    title="Cancel Task"
                    confirm-verb="Yes"
                    cancel-verb="No"
                    :cannot-undo="false"
                    :on-cancel="() => closeTaskModal('cancelWarning')"
                    :on-confirm="() => cancelTask({ documentId: id })"
                />
            </div>
        </template>
    </EscrPage>
</template>
<script>
import ReconnectingWebSocket from "reconnectingwebsocket";
import { mapActions, mapState } from "vuex";
import AlignModal from "../../components/AlignModal/AlignModal.vue";
import ExportModal from "../../components/ExportModal/ExportModal.vue";
import ArrowRightIcon from "../../components/Icons/ArrowRightIcon/ArrowRightIcon.vue";
import CharactersCard from "../../components/CharactersCard/CharactersCard.vue";
import ConfirmModal from "../../components/ConfirmModal/ConfirmModal.vue";
import EditDocumentModal from "../../components/EditDocumentModal/EditDocumentModal.vue";
import EscrButton from "../../components/Button/Button.vue";
import EscrDropdown from "../../components/Dropdown/Dropdown.vue";
import EscrPage from "../Page/Page.vue";
import EscrTags from "../../components/Tags/Tags.vue";
import EscrTable from "../../components/Table/Table.vue";
import ImportModal from "../../components/ImportModal/ImportModal.vue";
import ModelsIcon from "../../components/Icons/ModelsIcon/ModelsIcon.vue";
import ModelsPanel from "../../components/ModelsPanel/ModelsPanel.vue";
import OntologyCard from "../../components/OntologyCard/OntologyCard.vue";
import PencilIcon from "../../components/Icons/PencilIcon/PencilIcon.vue";
import PeopleIcon from "../../components/Icons/PeopleIcon/PeopleIcon.vue";
import QuickActionsPanel from "../../components/QuickActionsPanel/QuickActionsPanel.vue";
import SearchIcon from "../../components/Icons/SearchIcon/SearchIcon.vue";
import SearchPanel from "../../components/SearchPanel/SearchPanel.vue";
import SegmentModal from "../../components/SegmentModal/SegmentModal.vue";
import ShareModal from "../../components/SharePanel/ShareModal.vue";
import SharePanel from "../../components/SharePanel/SharePanel.vue";
import TaskDashboard from "./TaskDashboard.vue";
import ToolsIcon from "../../components/Icons/ToolsIcon/ToolsIcon.vue";
import TrashIcon from "../../components/Icons/TrashIcon/TrashIcon.vue";
import TranscribeModal from "../../components/TranscribeModal/TranscribeModal.vue";
import VerticalMenu from "../../components/VerticalMenu/VerticalMenu.vue";
import "./Document.css";

export default {
    name: "EscrDocumentDashboard",
    components: {
        AlignModal,
        ArrowRightIcon,
        CharactersCard,
        ConfirmModal,
        EditDocumentModal,
        EscrButton,
        EscrDropdown,
        EscrPage,
        EscrTable,
        EscrTags,
        ExportModal,
        ImportModal,
        // eslint-disable-next-line vue/no-unused-components
        ModelsIcon,
        // eslint-disable-next-line vue/no-unused-components
        ModelsPanel,
        OntologyCard,
        // eslint-disable-next-line vue/no-unused-components
        PeopleIcon,
        // eslint-disable-next-line vue/no-unused-components
        PencilIcon,
        // eslint-disable-next-line vue/no-unused-components
        QuickActionsPanel,
        // eslint-disable-next-line vue/no-unused-components
        SearchIcon,
        // eslint-disable-next-line vue/no-unused-components
        SearchPanel,
        SegmentModal,
        ShareModal,
        // eslint-disable-next-line vue/no-unused-components
        SharePanel,
        TaskDashboard,
        // eslint-disable-next-line vue/no-unused-components
        ToolsIcon,
        // eslint-disable-next-line vue/no-unused-components
        TrashIcon,
        TranscribeModal,
        VerticalMenu,
    },
    props: {
        /**
         * The primary key/id of the current document.
         */
        id: {
            type: Number,
            required: true,
        }
    },
    data() {
        return {
            msgSocket: undefined,
        };
    },
    computed: {
        ...mapState({
            allDocumentTags: (state) => state.project.documentTags,
            charCount: (state) => state.transcription.characterCount,
            characters: (state) => state.characters.characters,
            charactersLoading: (state) => state.characters.loading,
            charactersSort: (state) => state.characters.sortState,
            documentMenuOpen: (state) => state.document.menuOpen,
            documentMetadata: (state) => state.document.metadata,
            documentName: (state) => state.document.name,
            deleteModalOpen: (state) => state.document.deleteModalOpen,
            editModalOpen: (state) => state.document.editModalOpen,
            groups: (state) => state.user.groups,
            lineCount: (state) => state.transcription.lineCount,
            loading: (state) => state.document.loading,
            mainScript: (state) => state.document.mainScript,
            models: (state) => state.document.models,
            nextPage: (state) => state.document.nextPage,
            ontology: (state) => state.ontology.ontology,
            ontologyCategory: (state) => state.ontology.category,
            ontologyLoading: (state) => state.ontology.loading,
            parts: (state) => state.document.parts,
            partsCount: (state) => state.document.partsCount,
            projectId: (state) => state.document.projectId,
            projectName: (state) => state.document.projectName,
            recognitionModels: (state) => state.user.recognitionModels,
            regionTypes: (state) => state.document.regionTypes,
            segmentationModels: (state) => state.user.segmentationModels,
            selectedTranscription: (state) => state.transcription.selectedTranscription,
            scripts: (state) => state.project.scripts,
            sharedWithUsers: (state) => state.document.sharedWithUsers,
            sharedWithGroups: (state) => state.document.sharedWithGroups,
            shareModalOpen: (state) => state.document.shareModalOpen,
            tags: (state) => state.document.tags,
            tagsModalOpen: (state) => state.document.tagsModalOpen,
            taskModalOpen: (state) => state.tasks.modalOpen,
            textualWitnesses: (state) => state.document.textualWitnesses,
            transcriptionLoading: (state) => state.transcription.loading,
            transcriptions: (state) => state.document.transcriptions,
        }),
        /**
         * Links and titles for the breadcrumbs above the page.
         */
        breadcrumbs() {
            let docBreadcrumbs = [{ title: "Loading..." }];
            if (this.projectName && this.projectId && this.documentName) {
                docBreadcrumbs = [
                    {
                        title: this.projectName,
                        href: `/projects/${this.projectId}`
                    },
                    { title: this.documentName }
                ];
            }
            return [
                { title: "My Projects", href: "/projects" },
                ...docBreadcrumbs,
            ];
        },
        /**
         * Menu items for the vertical menu in the top right corner of the dashboard.
         */
        documentMenuItems() {
            return [
                {
                    icon: PencilIcon,
                    key: "edit",
                    label: "Edit",
                    onClick: this.openEditModal,
                },
                {
                    icon: TrashIcon,
                    key: "delete",
                    label: "Delete Document",
                    onClick: this.openDeleteModal,
                }
            ]
        },
        /**
         * Headers for the parts (images) table.
         */
        partsHeaders() {
            return [
                { label: "Name", value: "title", image: "thumbnail" },
                {
                    label: "Last Update",
                    value: "updated_at",
                    format: (val) => new Date(val).toLocaleDateString(
                        undefined,
                        { year: "numeric", month: "long", day: "numeric" },
                    ),
                },
            ];
        },
        /**
         * Sidebar quick actions for the document dashboard.
         */
        sidebarActions() {
            return [
                {
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
                },
                {
                    data: {
                        disabled: this.loading?.document,
                        scope: "Document",
                    },
                    icon: ToolsIcon,
                    key: "tasks",
                    label: "Quick Actions",
                    panel: QuickActionsPanel,
                },
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
                    label: "Document Models",
                    panel: ModelsPanel,
                }
            ];
        },
        transcriptionConfidence() {
            const confidence = this.transcriptions?.find(
                (transcription) => transcription.pk === this.selectedTranscription
            )?.avg_confidence;
            return confidence ? `${Math.round(confidence * 100)}%` : "N/A";
        },
        transcriptionLevels() {
            return this.transcriptions.map((transcription) => ({
                value: transcription.pk,
                selected: transcription.pk === this.selectedTranscription,
                label: transcription.name,
            }));
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
        try {
            await this.fetchDocument();
        } catch (error) {
            this.setLoading({ key: "document", loading: false });
            this.addError(error);
        }
        try {
            this.setLoading({ key: "user", loading: true });
            await this.fetchGroups();
            this.setLoading({ key: "user", loading: false });
        } catch(error) {
            this.setLoading({ key: "user", loading: false });
            this.addError(error);
        }
    },
    methods: {
        ...mapActions("document", [
            "changeOntologyCategory",
            "changeSelectedTranscription",
            "closeDeleteModal",
            "closeDocumentMenu",
            "closeEditModal",
            "closeShareModal",
            "confirmOverwriteWarning",
            "deleteDocument",
            "fetchDocument",
            "fetchDocumentTasksThrottled",
            "handleSubmitAlign",
            "handleSubmitExport",
            "handleSubmitImport",
            "handleSubmitSegmentation",
            "handleSubmitTranscribe",
            "openCharactersModal",
            "openDeleteModal",
            "openDocumentMenu",
            "openEditModal",
            "openOntologyModal",
            "openShareModal",
            "openTagsModal",
            "saveDocument",
            "selectTranscription",
            "setId",
            "setLoading",
            "shareDocument",
            "sortCharacters",
            "sortOntology",
            "viewTasks",
        ]),
        ...mapActions("alerts", ["addError"]),
        ...mapActions("project", ["createNewDocumentTag"]),
        ...mapActions("user", ["fetchGroups"]),
        ...mapActions("tasks", {
            cancelTask: "cancel",
            closeTaskModal: "closeModal",
            align: "alignDocument",
            transcribe: "transcribeDocument",
            export: "exportDocument",
        }),
        navigateToImages() {
            if (this.id) {
                window.location = `/document/${this.id}/images`;
            } else {
                this.addError({ message: "Error navigating to the images page." });
            }
        },
        navigateToTasks() {
            window.location = "/quotas/";
        },
        selectTranscription(e) {
            this.changeSelectedTranscription(parseInt(e.target.value, 10));
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
                // these may be frequent, so throttle
                this.fetchDocumentTasksThrottled();
            }
        }
    },
}
</script>
