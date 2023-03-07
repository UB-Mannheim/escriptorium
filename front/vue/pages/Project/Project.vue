<template>
    <EscrPage class="escr-project-dashboard">
        <template #page-content>
            <div class="escr-card escr-card-padding project-details">
                <div class="escr-card-header">
                    <h1>{{ projectName }}</h1>
                    <div class="escr-card-actions">
                        <EscrButton
                            label="Edit"
                            size="small"
                            :on-click="openEditModal"
                            :disabled="loading || editModalOpen"
                        >
                            <template #button-icon>
                                <PencilIcon />
                            </template>
                        </EscrButton>
                    </div>
                </div>
                Project Guidelines
            </div>
            <div class="escr-card escr-card-table project-documents-list">
                <div class="escr-card-header">
                    <h2>Documents</h2>
                </div>
                <EscrTable
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
                            :on-click="() => openDeleteModal(item)"
                            :disabled="loading"
                            aria-label="Delete document"
                        >
                            <template #button-icon>
                                <TrashIcon />
                            </template>
                        </EscrButton>
                    </template>
                </EscrTable>
            </div>
            <OntologyCard
                class="project-ontology"
                context="Project"
                :items="ontology"
                :loading="loading"
                :on-view="() => openOntologyModal"
                :on-select-category="changeOntologyCategory"
                :on-sort="sortOntology"
                :selected-category="ontologyCategory"
            />
            <CharactersCard
                class="project-characters"
                :loading="loading"
                :on-view="() => openCharactersModal"
                :on-sort-characters="sortCharacters"
                :sort="charactersSort?.field"
                :items="characters"
            />
        </template>
    </EscrPage>
</template>
<script>
import { mapActions, mapState } from "vuex";
import EscrButton from "../../components/Button/Button.vue";
import EscrPage from "../Page/Page.vue";
import EscrTable from "../../components/Table/Table.vue";
import EscrTags from "../../components/Tags/Tags.vue";
import CharactersCard from "../../components/CharactersCard/CharactersCard.vue";
import ImagesIcon from "../../components/Icons/ImagesIcon/ImagesIcon.vue";
import OntologyCard from "../../components/OntologyCard/OntologyCard.vue";
import PencilIcon from "../../components/Icons/PencilIcon/PencilIcon.vue";
import TrashIcon from "../../components/Icons/TrashIcon/TrashIcon.vue";
import "./Project.css";

export default {
    name: "EscrProjectDashboard",
    components: {
        CharactersCard,
        EscrButton,
        EscrPage,
        EscrTable,
        ImagesIcon,
        OntologyCard,
        PencilIcon,
        TrashIcon,
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
            characters: (state) => state.project.characters,
            charactersSort: (state) => state.project.charactersSort,
            documents: (state) => state.project.documents,
            editModalOpen: (state) => state.project.editModalOpen,
            loading: (state) => state.project.loading,
            ontology: (state) => state.ontology.ontology,
            ontologyCategory: (state) => state.ontology.category,
            projectName: (state) => state.project.name,
        }),
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
    },
    /**
     * On load, fetch basic details about the project.
     */
    async created() {
        this.setId(this.id);
        try {
            await this.fetchProject();
            await this.fetchProjectDocuments();
            await this.fetchProjectOntology();
            await this.fetchProjectCharacters();
        } catch (error) {
            this.addError(error);
        }
    },
    methods: {
        ...mapActions("project", [
            "changeOntologyCategory",
            "fetchProject",
            "fetchProjectCharacters",
            "fetchProjectDocuments",
            "fetchProjectOntology",
            "openCharactersModal",
            "openEditModal",
            "openOntologyModal",
            "setId",
            "sortCharacters",
            "sortDocuments",
            "sortOntology",
        ]),
        ...mapActions("alerts", ["addError"]),
    },
}
</script>
