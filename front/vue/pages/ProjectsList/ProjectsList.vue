<template>
    <EscrPage class="escr-projects-list">
        <template #page-content>
            <h1>Welcome back, {{ firstName || username }}</h1>
            <div class="escr-card escr-card-table">
                <div class="escr-card-padding escr-card-header">
                    <h2>Projects</h2>
                    <div class="escr-card-actions">
                        <FilterSet
                            :disabled="loading"
                            :tags="tags"
                            :on-filter="async () => await fetchProjects()"
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
                        <NewProjectModal
                            v-if="createModalOpen"
                            :disabled="loading"
                            :new-project="true"
                            :on-save="createNewProject"
                            :on-cancel="closeCreateModal"
                            :on-create-tag="createNewProjectTag"
                            :tags="tags"
                        />
                    </div>
                </div>
                <EscrModal
                    v-if="deleteModalOpen"
                    class="escr-delete-project"
                >
                    <template #modal-content>
                        <h2>Delete Project "{{ projectToDelete.name }}"</h2>
                        <p>
                            Are you sure you want to delete this project?
                            This action cannot be undone.
                        </p>
                    </template>
                    <template #modal-actions>
                        <EscrButton
                            color="outline-primary"
                            label="Cancel"
                            :disabled="loading"
                            :on-click="() => closeDeleteModal()"
                        />
                        <EscrButton
                            color="danger"
                            label="Delete"
                            :disabled="loading"
                            :on-click="() => deleteProject()"
                        />
                    </template>
                </EscrModal>
                <div
                    v-if="projects.length"
                    class="table-container"
                >
                    <EscrTable
                        :items="projects"
                        item-key="slug"
                        :headers="headers"
                        :on-sort="sortProjects"
                        :disabled="loading"
                        :linkable="true"
                    >
                        <template #actions="{ item }">
                            <EscrButton
                                v-tooltip.bottom="'Delete'"
                                size="small"
                                color="text"
                                :on-click="() => openDeleteModal(item)"
                                :disabled="loading"
                                aria-label="Delete project"
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
                    no-data-message="There are no projects to display."
                />
            </div>
        </template>
    </EscrPage>
</template>
<script>
import { mapActions, mapState } from "vuex";
import EscrButton from "../../components/Button/Button.vue";
import EscrLoader from "../../components/Loader/Loader.vue";
import EscrModal from "../../components/Modal/Modal.vue";
import EscrPage from "../Page/Page.vue";
import EscrTable from "../../components/Table/Table.vue";
import EscrTags from "../../components/Tags/Tags.vue";
import FilterSet from "../../components/FilterSet/FilterSet.vue";
import NewProjectModal from "../../components/EditProjectModal/EditProjectModal.vue";
import PlusIcon from "../../components/Icons/PlusIcon/PlusIcon.vue";
import TrashIcon from "../../components/Icons/TrashIcon/TrashIcon.vue";
import "../../components/Common/Card.css"
import "./ProjectsList.css";

export default {
    name: "EscrProjectsListPage",
    components: {
        EscrButton,
        EscrLoader,
        EscrModal,
        EscrPage,
        EscrTable,
        // eslint-disable-next-line vue/no-unused-components
        EscrTags,
        FilterSet,
        NewProjectModal,
        PlusIcon,
        TrashIcon,
    },
    computed: {
        ...mapState({
            createModalOpen: (state) => state.projects.createModalOpen,
            deleteModalOpen: (state) => state.projects.deleteModalOpen,
            firstName: (state) => state.user.firstName,
            loading: (state) => state.projects.loading,
            nextPage: (state) => state.projects.nextPage,
            projects: (state) => state.projects.projects,
            projectToDelete: (state) => state.projects.projectToDelete,
            tags: (state) => state.projects.tags,
            username: (state) => state.user.username,
        }),
        headers() {
            return [
                { label: "Name", value: "name", sortable: true },
                { label: "Project Tags", value: "tags", component: EscrTags },
                { label: "# of Documents", value: "documents_count", sortable: true  },
                { label: "Owner", value: "owner", sortable: true  },
                {
                    label: "Last Update",
                    value: "updated_at",
                    sortable: true,
                    format: (val) => new Date(val).toLocaleDateString(
                        undefined,
                        { year: "numeric", month: "long", day: "numeric" },
                    ),
                },
            ];
        },
    },
    async created() {
        try {
            await this.fetchCurrentUser();
            await this.fetchProjects();
            await this.fetchAllProjectTags();
        } catch (error) {
            this.addError(error);
        }
    },
    methods: {
        ...mapActions("projects", [
            "closeCreateModal",
            "closeDeleteModal",
            "createNewProject",
            "createNewProjectTag",
            "deleteProject",
            "fetchAllProjectTags",
            "fetchProjects",
            "fetchNextPage",
            "openCreateModal",
            "openDeleteModal",
            "sortProjects",
        ]),
        ...mapActions("alerts", ["addError"]),
        ...mapActions("user", ["fetchCurrentUser"]),
    },
};
</script>
