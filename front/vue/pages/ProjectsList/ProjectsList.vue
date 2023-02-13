<template>
    <EscrPage class="escr-projects-list">
        <template #page-content>
            <h1>Welcome back, {{ user.first_name }}</h1>
            <div class="escr-card">
                <div class="escr-card-padding escr-card-header">
                    <h2>Projects</h2>
                    <div class="escr-card-actions">
                        <FilterSet
                            :tags="tags"
                            :on-filter="async () => await fetchProjects()"
                        />
                        <EscrButton
                            label="Create New"
                            :on-click="openCreateModal"
                            :disabled="createModalOpen"
                        >
                            <template #button-icon>
                                <PlusIcon />
                            </template>
                        </EscrButton>
                        <NewProjectModal
                            v-if="createModalOpen"
                            :create-disabled="!newProjectName"
                            :on-input="(e) => handleNewProjectNameInput(e.target.value)"
                            :on-create="() => createNewProject()"
                            :on-cancel="() => closeCreateModal()"
                        />
                    </div>
                </div>
                <EscrTable
                    v-if="projects.length"
                    :items="projects"
                    item-key="slug"
                    :headers="headers"
                    :on-sort="sortProjects"
                >
                    <template #actions>
                        <EscrButton
                            size="small"
                            color="text"
                            :on-click="(e) => {}"
                        >
                            <template #button-icon>
                                <TrashIcon />
                            </template>
                        </EscrButton>
                    </template>
                </EscrTable>
                <div
                    v-else
                    class="escr-empty-msg"
                >
                    There are no projects to display.
                </div>
            </div>
        </template>
    </EscrPage>
</template>
<script>
import EscrButton from "../../components/Button/Button.vue";
import EscrPage from "../Page/Page.vue";
import EscrTable from "../../components/Table/Table.vue";
import PlusIcon from "../../components/Icons/PlusIcon/PlusIcon.vue";
import TrashIcon from "../../components/Icons/TrashIcon/TrashIcon.vue";
import EscrTags from "../../components/Tags/Tags.vue";
import FilterSet from "../../components/FilterSet/FilterSet.vue";
import "./ProjectsList.css";
import { mapActions, mapState } from "vuex";
import NewProjectModal from "./NewProjectModal.vue";

export default {
    name: "EscrProjectsListPage",
    components: {
        EscrButton,
        EscrPage,
        EscrTable,
        // eslint-disable-next-line vue/no-unused-components
        EscrTags,
        FilterSet,
        NewProjectModal,
        PlusIcon,
        TrashIcon,
    },
    props: {
        user: {
            type: Object,
            required: true,
        },
    },
    computed: {
        ...mapState({
            createModalOpen: (state) => state.projects.createModalOpen,
            deleteModalOpen: (state) => state.projects.deleteModalOpen,
            newProjectName: (state) => state.projects.newProjectName,
            projects: (state) => state.projects.projects,
            tags: (state) => state.projects.tags,
        }),
        headers() {
            return [
                { label: "Name", value: "name", sortable: true },
                { label: "Project Tags", value: "tags", component: EscrTags },
                { label: "# of Documents", value: "documents_count", sortable: true  },
                { label: "Owner", value: "owner", sortable: true  },
                { label: "Last Update", value: "updated_at", sortable: true  },
            ];
        },
    },
    async created() {
        try {
            await this.fetchProjects();
            await this.fetchAllProjectTags();
        } catch (error) {
            this.addAlert(
                { color: "alert", message: error.message },
            );
            console.error(error);
        }
    },
    methods: {
        ...mapActions("projects", [
            "closeCreateModal",
            "createNewProject",
            "fetchAllProjectTags",
            "fetchProjects",
            "handleNewProjectNameInput",
            "openCreateModal",
            "sortProjects",
        ]),
        ...mapActions("alerts", { addAlert: "add" }),
    },
};
</script>
