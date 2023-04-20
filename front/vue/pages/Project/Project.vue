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
                                :on-filter="async () => await fetchProjectDocuments()"
                            />
                            <EscrButton
                                label="Create New"
                                :on-click="openCreateModal"
                                :disabled="loading || createModalOpen"
                            >
                                <template #button-icon>
                                    <PlusIcon />
                                </template>
                            </EscrButton>
                        </div>
                    </div>
                    <div class="table-container">
                        <EscrTable
                            v-if="documents.length"
                            item-key="pk"
                            :headers="headers"
                            :items="documents"
                            :on-sort="sortDocuments"
                            :sort-disabled="loading"
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
                        <div
                            v-else-if="!loading"
                            class="escr-empty-msg"
                        >
                            There are no documents to display.
                        </div>
                        <div
                            v-else
                            class="escr-empty-msg"
                        >
                            Loading...
                        </div>
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
                </div>
            </div>
        </template>
    </EscrPage>
</template>
<script>
import { mapActions, mapState } from "vuex";
import EditProjectModal from "../../components/EditProjectModal/EditProjectModal.vue";
import EscrButton from "../../components/Button/Button.vue";
import EscrPage from "../Page/Page.vue";
import EscrTable from "../../components/Table/Table.vue";
import EscrTags from "../../components/Tags/Tags.vue";
import FilterSet from "../../components/FilterSet/FilterSet.vue";
import ImagesIcon from "../../components/Icons/ImagesIcon/ImagesIcon.vue";
import PencilIcon from "../../components/Icons/PencilIcon/PencilIcon.vue";
import PeopleIcon from "../../components/Icons/PeopleIcon/PeopleIcon.vue";
import PlusIcon from "../../components/Icons/PlusIcon/PlusIcon.vue";
import SharePanel from "../../components/SharePanel/SharePanel.vue";
import TrashIcon from "../../components/Icons/TrashIcon/TrashIcon.vue";
import VerticalMenu from "../../components/VerticalMenu/VerticalMenu.vue";
import "./Project.css";

export default {
    name: "EscrProjectDashboard",
    components: {
        EditProjectModal,
        EscrButton,
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
        }
    },
    computed: {
        ...mapState({
            allProjectTags: (state) => state.projects.tags,
            createModalOpen: (state) => state.project.createModalOpen,
            documents: (state) => state.project.documents,
            documentTags: (state) => state.project.documentTags,
            editModalOpen: (state) => state.project.editModalOpen,
            guidelines: (state) => state.project.guidelines,
            loading: (state) => state.project.loading,
            nextPage: (state) => state.project.nextPage,
            projectName: (state) => state.project.name,
            projectMenuOpen: (state) => state.project.menuOpen,
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
            return [{
                data: {
                    users: this.sharedWithUsers,
                    groups: this.sharedWithGroups,
                    openShareModal: this.openShareModal,
                },
                icon: PeopleIcon,
                key: "share",
                label: "Groups & Users",
                panel: SharePanel,
            }];
        },
    },
    /**
     * On load, fetch basic details about the project.
     */
    async created() {
        this.setId(this.id);
        try {
            await this.fetchProject();
            await this.fetchProjectDocuments();
            await this.fetchProjectDocumentTags();
        } catch (error) {
            this.addError(error);
        }
    },
    methods: {
        ...mapActions("project", [
            "closeEditModal",
            "closeProjectMenu",
            "createNewProjectTag",
            "fetchNextPage",
            "fetchProject",
            "fetchProjectDocuments",
            "fetchProjectDocumentTags",
            "navigateToImages",
            "openCreateModal",
            "openDeleteModal",
            "openDeleteDocumentModal",
            "openEditModal",
            "openProjectMenu",
            "openShareModal",
            "saveProject",
            "setId",
            "sortDocuments",
        ]),
        ...mapActions("projects", ["fetchAllProjectTags"]),
        ...mapActions("alerts", ["addError"]),
    },
}
</script>
