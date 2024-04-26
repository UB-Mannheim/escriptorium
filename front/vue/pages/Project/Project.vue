<template>
    <EscrPage
        class="escr-project-dashboard"
        :breadcrumbs="breadcrumbs"
        :sidebar-actions="sidebarActions"
        :loading="loading"
    >
        <template #page-content>
            <div class="escr-grid-container">
                <!-- Project metadata header -->
                <div class="escr-card escr-card-padding escr-project-details">
                    <div class="escr-card-header">
                        <h1>{{ projectName }}</h1>
                        <div class="escr-card-actions">
                            <VerticalMenu
                                :is-open="projectMenuOpen"
                                :close-menu="closeProjectMenu"
                                :open-menu="openProjectMenu"
                                :disabled="loading"
                                :items="projectMenuItems"
                            />
                            <EditProjectModal
                                v-if="editModalOpen"
                                :disabled="loading"
                                :on-cancel="closeEditModal"
                                :on-create-tag="createNewProjectTag"
                                :on-save="saveProject"
                                :tags="allProjectTags"
                            />
                        </div>
                    </div>
                    <a
                        v-if="guidelines"
                        :href="guidelines"
                        class="escr-project-guidelines"
                    >
                        Project Guidelines
                    </a>
                    <EscrTags
                        v-if="tags"
                        :tags="tags"
                    />
                </div>
                <!-- Documents list -->
                <div class="escr-card escr-card-table escr-documents-list">
                    <div class="escr-card-header">
                        <h2>Documents</h2>
                        <div class="escr-card-actions">
                            <FilterSet
                                :disabled="loading"
                                :tags="documentTags"
                                :on-filter="onFilterDocuments"
                            />
                            <EscrButton
                                label="Create New"
                                :on-click="openCreateDocumentModal"
                                :disabled="loading || createDocumentModalOpen"
                            >
                                <template #button-icon>
                                    <PlusIcon />
                                </template>
                            </EscrButton>
                            <EditDocumentModal
                                v-if="createDocumentModalOpen"
                                :disabled="loading"
                                :new-document="true"
                                :on-cancel="closeCreateDocumentModal"
                                :on-create-tag="createNewDocumentTag"
                                :on-save="createNewDocument"
                                :scripts="scripts"
                                :tags="documentTags"
                            />
                        </div>
                    </div>
                    <div
                        v-if="documents.length"
                        class="table-container"
                    >
                        <EscrTable
                            item-key="pk"
                            :headers="headers"
                            :items="documents"
                            :on-sort="sortDocuments"
                            :disabled="loading"
                            :linkable="true"
                        >
                            <template #actions="{ item }">
                                <EscrButton
                                    v-tooltip.bottom="'Images'"
                                    size="small"
                                    color="text"
                                    :on-click="() => navigateToImages(item)"
                                    :disabled="loading"
                                    aria-label="Document images"
                                >
                                    <template #button-icon>
                                        <ImagesIcon />
                                    </template>
                                </EscrButton>
                                <EscrButton
                                    v-tooltip.bottom="'Delete'"
                                    size="small"
                                    color="text"
                                    :on-click="() => openDeleteDocumentModal(item)"
                                    :disabled="loading"
                                    aria-label="Delete document"
                                >
                                    <template #button-icon>
                                        <TrashIcon />
                                    </template>
                                </EscrButton>
                            </template>
                        </EscrTable>
                        <EscrButton
                            v-if="nextPage"
                            label="Load more"
                            class="escr-load-more-btn"
                            color="outline-primary"
                            size="small"
                            :disabled="loading"
                            :on-click="async () => await fetchNextPage()"
                        />
                    </div>
                    <EscrLoader
                        v-else
                        :loading="loading"
                        no-data-message="There are no documents to display."
                    />
                </div>
                <!-- delete project modal -->
                <ConfirmModal
                    v-if="deleteModalOpen"
                    body-text="Are you sure you want to delete this project?"
                    confirm-verb="Delete"
                    title="Delete Project"
                    :cannot-undo="true"
                    :disabled="loading"
                    :on-cancel="closeDeleteModal"
                    :on-confirm="deleteProject"
                />
                <!-- delete document modal -->
                <ConfirmModal
                    v-if="deleteDocumentModalOpen"
                    :body-text="`Are you sure you want to delete the document ${
                        (documentToDelete && documentToDelete.name) || ''
                    }?`"
                    confirm-verb="Delete"
                    :title="`Delete ${(documentToDelete && documentToDelete.name) || 'Document'}`"
                    :cannot-undo="true"
                    :disabled="loading"
                    :on-cancel="closeDeleteDocumentModal"
                    :on-confirm="deleteDocument"
                />
                <!-- share project modal -->
                <ShareModal
                    v-if="shareModalOpen"
                    :groups="groups"
                    :disabled="loading"
                    :on-cancel="closeShareModal"
                    :on-submit="share"
                />
            </div>
        </template>
    </EscrPage>
</template>
<script>
import { mapActions, mapState } from "vuex";
import ConfirmModal from "../../components/ConfirmModal/ConfirmModal.vue";
import EditDocumentModal from "../../components/EditDocumentModal/EditDocumentModal.vue";
import EditProjectModal from "../../components/EditProjectModal/EditProjectModal.vue";
import EscrButton from "../../components/Button/Button.vue";
import EscrLoader from "../../components/Loader/Loader.vue";
import EscrPage from "../Page/Page.vue";
import EscrTable from "../../components/Table/Table.vue";
import EscrTags from "../../components/Tags/Tags.vue";
import FilterSet from "../../components/FilterSet/FilterSet.vue";
import ImagesIcon from "../../components/Icons/ImagesIcon/ImagesIcon.vue";
import PencilIcon from "../../components/Icons/PencilIcon/PencilIcon.vue";
import PeopleIcon from "../../components/Icons/PeopleIcon/PeopleIcon.vue";
import PlusIcon from "../../components/Icons/PlusIcon/PlusIcon.vue";
import SearchIcon from "../../components/Icons/SearchIcon/SearchIcon.vue";
import SearchPanel from "../../components/SearchPanel/SearchPanel.vue";
import ShareModal from "../../components/SharePanel/ShareModal.vue";
import SharePanel from "../../components/SharePanel/SharePanel.vue";
import TrashIcon from "../../components/Icons/TrashIcon/TrashIcon.vue";
import VerticalMenu from "../../components/VerticalMenu/VerticalMenu.vue";
import "../../components/Common/Card.css"
import "./Project.css";

export default {
    name: "EscrProjectDashboard",
    components: {
        ConfirmModal,
        EditDocumentModal,
        EditProjectModal,
        EscrButton,
        EscrLoader,
        EscrPage,
        EscrTable,
        EscrTags,
        FilterSet,
        ImagesIcon,
        // eslint-disable-next-line vue/no-unused-components
        PencilIcon,
        // eslint-disable-next-line vue/no-unused-components
        PeopleIcon,
        PlusIcon,
        // eslint-disable-next-line vue/no-unused-components
        SearchPanel,
        ShareModal,
        // eslint-disable-next-line vue/no-unused-components
        SharePanel,
        TrashIcon,
        VerticalMenu,
    },
    props: {
        /**
         * The primary key/id of the current project.
         */
        id: {
            type: Number,
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
    computed: {
        ...mapState({
            allProjectTags: (state) => state.projects.tags,
            createDocumentModalOpen: (state) => state.project.createDocumentModalOpen,
            deleteModalOpen: (state) => state.project.deleteModalOpen,
            deleteDocumentModalOpen: (state) => state.project.deleteDocumentModalOpen,
            documents: (state) => state.project.documents,
            documentTags: (state) => state.project.documentTags,
            documentToDelete: (state) => state.project.documentToDelete,
            editModalOpen: (state) => state.project.editModalOpen,
            groups: (state) => state.user.groups,
            guidelines: (state) => state.project.guidelines,
            loading: (state) => state.project.loading,
            nextPage: (state) => state.project.nextPage,
            projectName: (state) => state.project.name,
            projectId: (state) => state.project.id,
            projectMenuOpen: (state) => state.project.menuOpen,
            scripts: (state) => state.project.scripts,
            shareModalOpen: (state) => state.project.shareModalOpen,
            sharedWithUsers: (state) => state.project.sharedWithUsers,
            sharedWithGroups: (state) => state.project.sharedWithGroups,
            tags: (state) => state.project.tags,
        }),
        /**
         * Links and titles for the breadcrumbs above the page.
         */
        breadcrumbs() {
            return [
                { title: "My Projects", href: "/projects" },
                { title: this.projectName || "Loading..." }
            ];
        },
        /**
         * Table headers for the document list in the project dashboard.
         */
        headers() {
            return [
                { label: "Name", value: "name", sortable: true },
                { label: "Document Tags", value: "tags", component: EscrTags },
                { label: "# of Images", value: "parts_count", sortable: true  },
                {
                    label: "Last Update",
                    value: "updated_at",
                    sortable: true,
                    format: (val) => new Date(val).toLocaleDateString(
                        undefined,
                        { year: "numeric", month: "long", day: "numeric" },
                    ),
                },
                // { label: "Default Transcription Level", value: "default_transcription_level"  },
            ];
        },
        /**
         * Menu items for the vertical menu in the top right corner of the dashboard.
         */
        projectMenuItems() {
            return [
                {
                    icon: PencilIcon,
                    key: "edit",
                    label: "Edit",
                    onClick: this.openEditModal,
                },
                {
                    icon: TrashIcon,
                    // Add the "new-section" class if/when there is more than one item above this
                    // class: "new-section",
                    key: "delete",
                    label: "Delete Project",
                    onClick: this.openDeleteModal,
                }
            ]
        },
        /**
         * Sidebar quick actions for the project dashboard.
         */
        sidebarActions() {
            let actions = [
                {
                    data: {
                        disabled: this.loading,
                        users: this.sharedWithUsers,
                        groups: this.sharedWithGroups,
                        openShareModal: this.openShareModal,
                    },
                    icon: PeopleIcon,
                    key: "share",
                    label: "Groups & Users",
                    panel: SharePanel,
                },
            ];
            // if search is enabled on the instance, add search as first item
            if (!this.searchDisabled) {
                actions.unshift({
                    data: {
                        disabled: this.loading,
                        projectId: this.projectId,
                        searchScope: "Project",
                    },
                    icon: SearchIcon,
                    key: "search",
                    label: "Search Project",
                    panel: SearchPanel,
                });
            }
            return actions;
        },
    },
    /**
     * On load, fetch basic details about the project.
     */
    async created() {
        this.setLoading(true);
        this.setId(this.id);
        try {
            await this.fetchProject();
            await this.fetchGroups();
        } catch (error) {
            this.addError(error);
        }
        this.setLoading(false);
    },
    methods: {
        ...mapActions("project", [
            "closeCreateDocumentModal",
            "closeDeleteModal",
            "closeDeleteDocumentModal",
            "closeEditModal",
            "closeProjectMenu",
            "closeShareModal",
            "createNewDocumentTag",
            "createNewDocument",
            "createNewProjectTag",
            "deleteDocument",
            "deleteProject",
            "fetchNextPage",
            "fetchProject",
            "fetchProjectDocuments",
            "openCreateDocumentModal",
            "openDeleteModal",
            "openDeleteDocumentModal",
            "openEditModal",
            "openProjectMenu",
            "openShareModal",
            "searchProject",
            "saveProject",
            "setDocumentToDelete",
            "setId",
            "setLoading",
            "share",
            "sortDocuments",
        ]),
        ...mapActions("projects", ["fetchAllProjectTags"]),
        ...mapActions("user", ["fetchGroups"]),
        ...mapActions("alerts", ["addError"]),
        async onFilterDocuments() {
            this.setLoading(true);
            try {
                await this.fetchProjectDocuments();
            } catch (error) {
                this.addError(error);
            }
            this.setLoading(false);
        },
        navigateToImages(item) {
            if (item?.pk) {
                window.location = `/document/${item.pk}/images`;
            } else {
                this.addError({ message: "Error navigating to the images page." });
            }
        },
    },
}
</script>
