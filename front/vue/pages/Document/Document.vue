<template>
    <EscrPage
        class="escr-document-dashboard"
        :breadcrumbs="breadcrumbs"
        :sidebar-actions="sidebarActions"
        :loading="loading?.document"
    >
        <template #page-content>
            <div class="escr-grid-container">
                <div class="escr-doc-left-grid">
                    <!-- Document metadata header -->
                    <div class="escr-card escr-card-padding escr-document-details">
                        <div class="escr-card-header">
                            <h1>{{ documentName }}</h1>
                            <div class="escr-card-actions">
                                <EscrButton
                                    label="Edit"
                                    size="small"
                                    :on-click="openEditModal"
                                    :disabled="loading?.document || editModalOpen"
                                >
                                    <template #button-icon>
                                        <PencilIcon />
                                    </template>
                                </EscrButton>
                            </div>
                        </div>
                        <!-- TODO: figure out what metadata should go here, handle appropriately -->
                        <span class="escr-document-metadata">
                            Main script: {{ mainScript }}
                        </span>
                    </div>

                    <!-- Document tags card -->
                    <div class="escr-card escr-card-padding escr-document-tags">
                        <div class="escr-card-header">
                            <h2>Tags</h2>
                            <div class="escr-card-actions">
                                <EscrButton
                                    label="Edit"
                                    size="small"
                                    :on-click="openTagsModal"
                                    :disabled="loading?.document || tagsModalOpen"
                                >
                                    <template #button-icon>
                                        <PencilIcon />
                                    </template>
                                </EscrButton>
                            </div>
                        </div>
                        <EscrTags
                            v-if="tags"
                            :tags="tags"
                            wrap
                        />
                    </div>

                    <!-- Document tasks card -->
                    <div class="escr-card escr-card-padding escr-document-tasks">
                        <div class="escr-card-header">
                            <h2>Tasks</h2>
                            <div class="escr-card-actions">
                                <EscrButton
                                    label="View All"
                                    size="small"
                                    :on-click="viewTasks"
                                    :disabled="loading?.document"
                                >
                                    <template #button-icon-right>
                                        <ArrowRightIcon />
                                    </template>
                                </EscrButton>
                            </div>
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
                                    :on-click="viewTasks"
                                    :disabled="loading?.parts"
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
                                :disabled="loading?.transcriptions"
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
                        :sort="charactersSort?.field"
                        :items="characters"
                    />
                </div>
            </div>
        </template>
    </EscrPage>
</template>
<script>
import { mapActions, mapState } from "vuex";
import ArrowRightIcon from "../../components/Icons/ArrowRightIcon/ArrowRightIcon.vue";
import CharactersCard from "../../components/CharactersCard/CharactersCard.vue";
import EscrButton from "../../components/Button/Button.vue";
import EscrDropdown from "../../components/Dropdown/Dropdown.vue";
import EscrPage from "../Page/Page.vue";
import EscrTags from "../../components/Tags/Tags.vue";
import EscrTable from "../../components/Table/Table.vue";
import OntologyCard from "../../components/OntologyCard/OntologyCard.vue";
import PencilIcon from "../../components/Icons/PencilIcon/PencilIcon.vue";
import PeopleIcon from "../../components/Icons/PeopleIcon/PeopleIcon.vue";
import SearchIcon from "../../components/Icons/SearchIcon/SearchIcon.vue";
import SearchPanel from "../../components/SearchPanel/SearchPanel.vue";
import SharePanel from "../../components/SharePanel/SharePanel.vue";
import "./Document.css";

export default {
    name: "EscrDocumentDashboard",
    components: {
        ArrowRightIcon,
        CharactersCard,
        EscrButton,
        EscrDropdown,
        EscrPage,
        EscrTable,
        EscrTags,
        OntologyCard,
        // eslint-disable-next-line vue/no-unused-components
        PeopleIcon,
        PencilIcon,
        // eslint-disable-next-line vue/no-unused-components
        SearchIcon,
        // eslint-disable-next-line vue/no-unused-components
        SearchPanel,
        // eslint-disable-next-line vue/no-unused-components
        SharePanel,
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
    computed: {
        ...mapState({
            charCount: (state) => state.transcription.characterCount,
            characters: (state) => state.characters.characters,
            charactersLoading: (state) => state.characters.loading,
            charactersSort: (state) => state.characters.sortState,
            documentName: (state) => state.document.name,
            editModalOpen: (state) => state.document.editModalOpen,
            lineCount: (state) => state.transcription.lineCount,
            loading: (state) => state.document.loading,
            mainScript: (state) => state.document.mainScript,
            nextPage: (state) => state.document.nextPage,
            ontology: (state) => state.ontology.ontology,
            ontologyCategory: (state) => state.ontology.category,
            ontologyLoading: (state) => state.ontology.loading,
            parts: (state) => state.document.parts,
            partsCount: (state) => state.document.partsCount,
            projectId: (state) => state.document.projectId,
            projectName: (state) => state.document.projectName,
            selectedTranscription: (state) => state.transcription.selectedTranscription,
            sharedWithUsers: (state) => state.document.sharedWithUsers,
            sharedWithGroups: (state) => state.document.sharedWithGroups,
            tags: (state) => state.document.tags,
            tagsModalOpen: (state) => state.document.tagsModalOpen,
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
            return [{
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
        try {
            await this.fetchDocument();
        } catch (error) {
            this.setLoading("document", false);
            this.addError(error);
        }
    },
    methods: {
        ...mapActions("document", [
            "changeOntologyCategory",
            "changeSelectedTranscription",
            "fetchDocument",
            "fetchTranscriptionCharacters",
            "fetchTranscriptionOntology",
            "openCharactersModal",
            "openEditModal",
            "openOntologyModal",
            "openShareModal",
            "openTagsModal",
            "selectTranscription",
            "setId",
            "setLoading",
            "sortCharacters",
            "sortOntology",
            "viewTasks",
        ]),
        ...mapActions("alerts", ["addError"]),
        selectTranscription(e) {
            this.changeSelectedTranscription(parseInt(e.target.value, 10));
        },
    },
}
</script>
