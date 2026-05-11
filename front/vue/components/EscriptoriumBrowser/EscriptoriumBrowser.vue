<template>
    <div class="escr-browser escr-card">
        <div class="escr-card-header">
            <h3 class="escr-browser-breadcrumbs">
                <span v-if="!currentProject">Projects</span>
                <template v-else>
                    <a
                        href="#"
                        @click.prevent="fetchProjects"
                    > Projects </a>
                    <span class="separator italic">></span>
                    <span
                        v-if="!currentDocument"
                        class="italic"
                    >
                        {{ currentProject.name }}
                    </span>
                    <template v-else>
                        <a
                            href="#"
                            class="italic"
                            @click.prevent="resetDocumentSelection"
                        >
                            {{ currentProject.name }}
                        </a>
                        <span class="separator italic">></span>
                        <span>{{ currentDocument.name }}</span>
                    </template>
                </template>
            </h3>
            <div class="escr-browser-filters">
                <FilterSet
                    :disabled="loading"
                    :on-filter="handleFilter"
                    :search-placeholder="
                        currentDocument ? 'Search images...' :
                        currentProject ? 'Search documents...' :
                        'Search projects...'
                    "
                    :tags="currentTags"
                    :hide-tags="!!currentDocument"
                />
            </div>
        </div>
        <div
            class="escr-card-content escr-browser"
            @scroll="handleScroll"
        >
            <!-- Projects list -->
            <div v-if="!currentProject && !currentDocument">
                <EscrLoader
                    v-if="!projects || projects.length === 0"
                    :loading="loading"
                    no-data-message="No projects to display."
                />
                <template v-else>
                    <EscrTable
                        item-key="id"
                        :headers="projectHeaders"
                        :items="projects"
                        :disabled="loading"
                        :on-row-click="setCurrentProject"
                        :on-sort="sortProjects"
                    />
                    <div
                        v-if="isFetchingMoreProjects"
                        style="display: flex; justify-content: center; padding: 1rem;"
                    >
                        <div
                            class="escr-spinner escr-spinner--secondary"
                            role="status"
                        >
                            <span class="sr-only">Loading more...</span>
                        </div>
                    </div>
                </template>
            </div>
            <!-- Documents list -->
            <div
                v-if="currentProject && !currentDocument"
                class="escr-browser-documents-list"
            >
                <EscrLoader
                    v-if="!storeDocuments || storeDocuments.length === 0"
                    :loading="isFetchingContent"
                    no-data-message="No documents to display."
                />
                <template v-else>
                    <EscrTable
                        item-key="pk"
                        :headers="documentHeaders"
                        :items="storeDocuments"
                        :selectable="true"
                        :disabled="isUpdatingSelection"
                        :selected-items="fullySelectedDocs"
                        :partially-selected-items="partiallySelectedDocs"
                        :on-toggle-selected="handleToggleDocument"
                        :on-select-all="handleSelectAllDocuments"
                        :on-row-click="setCurrentDocument"
                        :on-sort="sortDocuments"
                    />
                    <div
                        v-if="isFetchingMoreDocuments"
                        style="display: flex; justify-content: center; padding: 1rem;"
                    >
                        <div
                            class="escr-spinner escr-spinner--secondary"
                            role="status"
                        >
                            <span class="sr-only">Loading more...</span>
                        </div>
                    </div>
                </template>
                <div
                    v-if="isUpdatingSelection"
                    class="images-loading-overlay no-bg"
                >
                    <div
                        class="escr-spinner"
                        role="status"
                    >
                        <span class="sr-only">Updating...</span>
                    </div>
                </div>
            </div>
            <!-- Images list -->
            <BrowserImageGrid
                v-if="currentDocument"
                :document="currentDocument"
                :pages="storePages"
                :is-fetching="isFetchingContent"
                :is-updating="isUpdatingSelection"
                :is-loading-more="loading"
                :has-next-page="!!nextPage"
                :all-selected="isDocumentFullySelected(currentDocument)"
                :has-selections="currentDocHasSelections"
                :transcription-options="transcriptionOptions"
                :default-transcription-id="defaultTranscription"
                :check-selected="isPageSelected"
                @toggle-all="toggleBrowserSelectAll"
                @deselect-all="browserDeselectAll"
                @change-default="handleDefaultTranscriptionChange"
                @apply-default="applyDefaultTranscription"
                @toggle-page="togglePageSelection"
                @update-transcription="handleUpdateTranscription"
                @load-more="onLoadMore"
                @select-visible="handleSelectVisible"
            />
        </div>
    </div>
</template>

<script>
import { mapActions, mapState } from "vuex";
import EscrTable from "../Table/Table.vue";
import EscrLoader from "../Loader/Loader.vue";
import EscrTags from "../Tags/Tags.vue";
import FilterSet from "../FilterSet/FilterSet.vue";
import BrowserImageGrid from "./BrowserImageGrid.vue";
import "./EscriptoriumBrowser.css";
import "../../pages/Images/Images.css";

export default {
    name: "EscriptoriumBrowser",
    components: {
        BrowserImageGrid,
        EscrLoader,
        EscrTable,
        // eslint-disable-next-line vue/no-unused-components
        EscrTags,
        FilterSet,
    },
    props: {
        /**
         * A project object (id, name) if one was already preselected on mount
         */
        preselectedProject: {
            type: Object,
            default: null,
        },
        /**
         * A document object if one was already preselected on mount
         */
        preselectedDocument: {
            type: Object,
            default: null,
        },
    },
    data() {
        return {
            currentProject: null,
            currentDocument: null,
            isFetchingContent: false,
            isFetchingMore: false,
            isFetchingMoreProjects: false,
            isFetchingMoreDocuments: false,
            isUpdatingSelection: false,
        };
    },
    computed: {
        ...mapState("projects", {
            projects: "projects",
            loading: "loading",
            projectTags: "tags",
            projectsNextPage: "nextPage",
        }),
        ...mapState("project", {
            storeDocuments: "documents",
            documentTags: "documentTags",
            documentsNextPage: "nextPage",
        }),
        ...mapState("document", { storePages: "parts" }),
        ...mapState("collection", {
            collectionItems: (state) => state.currentCollection.items,
            defaultTranscriptions: (state) =>
                state.currentCollection.defaultTranscriptions,
        }),
        ...mapState("images", ["nextPage"]),
        projectHeaders() {
            return [
                { label: "Project Name", value: "name", sortable: true, class: "col-title" },
                { label: "Tags", value: "tags", component: EscrTags, class: "col-tags" },
                {
                    label: "Documents",
                    value: "documents_count",
                    sortable: true,
                    class: "col-small",
                },
                {
                    label: "Updated At",
                    value: "updated_at",
                    format: this.formatDate,
                    sortable: true,
                    class: "col-date",
                },
            ];
        },
        documentHeaders() {
            return [
                { label: "Document Name", value: "name", sortable: true, class: "col-title" },
                { label: "Tags", value: "tags", component: EscrTags, class: "col-tags" },
                { label: "Pages", value: "parts_count", sortable: true, class: "col-small" },
                {
                    label: "Updated At",
                    value: "updated_at",
                    format: this.formatDate,
                    class: "col-date",
                    sortable: true,
                },
            ];
        },
        collectionsOptions() {
            return this.collections.map((c) => ({
                value: String(c.id),
                label: c.name,
                selected: c.id === this.collectionId,
            }));
        },
        /**
         * A cached Set of all selected part PKs
         */
        selectedPartIdsSet() {
            return new Set(this.collectionItems.map((i) => i.document_part));
        },

        /**
         * True if a specific part pk is currently staged in the collection store
         */
        isPageSelected() {
            return (partPK) => this.selectedPartIdsSet.has(partPK);
        },

        /**
         * True if all parts of a given document are currently staged in the collection store
         */
        isDocumentFullySelected() {
            return (doc) => {
                const docItems = this.collectionItems.filter(
                    (i) => i.document_id === doc.pk,
                );
                return (
                    docItems.length > 0 && docItems.length === doc.parts_count
                );
            };
        },

        /**
         * Array of unique document PKs where ALL pages are selected
         */
        fullySelectedDocs() {
            return this.storeDocuments
                .filter((doc) => this.isDocumentFullySelected(doc))
                .map((doc) => doc.pk);
        },

        /**
         * Array of unique document PKs where some, but not all, pages are selected
         */
        partiallySelectedDocs() {
            return this.storeDocuments
                .filter((doc) => {
                    const selectedCount = this.collectionItems.filter(
                        (i) => i.document_id === doc.pk,
                    ).length;
                    return selectedCount > 0 && selectedCount < doc.parts_count;
                })
                .map((doc) => doc.pk);
        },

        /**
         * The current document's default transcription layer
         */
        defaultTranscription() {
            if (!this.currentDocument) return null;
            // pull from stored default if exists
            const existingDefault = this.defaultTranscriptions[this.currentDocument.pk];
            if (existingDefault) return existingDefault;
            // otherwise, use "manual" or first transcription
            if (this.currentDocument.transcriptions?.length) {
                const manual = this.currentDocument.transcriptions.find(
                    (t) => t.name === "manual"
                );
                const firstTranscription = this.currentDocument.transcriptions[0];
                return manual
                    ? (manual.id || manual.pk)
                    : (firstTranscription.id ||firstTranscription.pk);
            }
            return null;
        },

        /**
         * Options for the default transcription select dropdown
         */
        transcriptionOptions() {
            if (!this.currentDocument?.transcriptions) return [];

            return this.currentDocument.transcriptions.map((t) => {
                const id = t.id || t.pk;
                return {
                    value: String(id), // Cast to string to match HTML values
                    label: t.name,
                    selected: id === this.defaultTranscription,
                };
            });
        },

        /**
         * Tags on the currently visible items
         */
        currentTags() {
            return this.currentProject ? this.documentTags : this.projectTags;
        },

        /**
         * True if the currently viewed document has any selected parts
         */
        currentDocHasSelections() {
            if (!this.currentDocument) return false;
            return this.collectionItems.some(
                (item) => item.document_id === this.currentDocument.pk
            );
        },
    },
    async mounted() {
        if (this.preselectedProject && this.preselectedDocument) {
            // fetch all projects and tags for breadcrumbs and search
            this.fetchStoreProjects();
            this.fetchAllProjectTags();

            // set project on state, fetch its documents
            this.currentProject = this.preselectedProject;
            this.setProjectId(this.preselectedProject.id);
            this.fetchProjectDocuments();

            // set document on state, wait for pages to load
            this.currentDocument = this.preselectedDocument;
            this.setDocumentId(this.preselectedDocument.pk);
            this.isFetchingContent = true;
            await this.fetchDocument();
            this.isFetchingContent = false;
        } else {
            // otherwise, just start at the project root list
            this.fetchProjects();
        }
    },
    methods: {
        ...mapActions("projects", {
            fetchStoreProjects: "fetchProjects",
            fetchAllProjectTags: "fetchAllProjectTags",
            fetchNextProjectsPage: "fetchNextPage",
            sortProjects: "sortProjects",
        }),
        ...mapActions("project", {
            setProjectId: "setId",
            fetchProjectDocuments: "fetchProjectDocuments",
            fetchProjectDocumentTags: "fetchProjectDocumentTags",
            fetchNextDocumentsPage: "fetchNextPage",
            sortDocuments: "sortDocuments",
        }),
        ...mapActions("document", {
            setDocumentId: "setId",
        }),
        ...mapActions("collection", [
            "addSelectedParts",
            "addAllParts",
            "removeItem",
        ]),
        ...mapActions("images", ["fetchDocument", "fetchNextPage", "fetchParts"]),
        ...mapActions("filter", ["removeFilter"]),

        /**
         * Load more images
         */
        async onLoadMore() {
            this.isFetchingMore = true;
            try {
                await this.fetchNextPage();
            } catch (error) {
                console.error("Failed to fetch next page:", error);
            } finally {
                this.isFetchingMore = false;
            }
        },

        /**
         * Format an ISO date string
         * @param {String} d Date string
         */
        formatDate(d) {
            if (!d) return "";
            const date = new Date(d);
            return new Intl.DateTimeFormat("en-US", {
                dateStyle: "medium",
                timeStyle: "short",
            }).format(date);
        },

        /**
         * Reset navigation state and fetch the root project list
         */
        async fetchProjects() {
            this.removeFilter("name");
            this.removeFilter("tags");
            this.resetAll();
            await Promise.all([
                this.fetchStoreProjects(),
                this.fetchAllProjectTags(),
            ]);
        },

        /**
         * Set the selected project state and fetch its child documents, triggered by clicking a row
         * in the Projects table
         * @param {Object} item Project object
         */
        async setCurrentProject(item) {
            this.removeFilter("name");
            this.removeFilter("tags");
            const project = this.projects.find((p) => p.id === item.id);
            this.currentProject = project;
            this.setProjectId(item.id);
            this.isFetchingContent = true;
            await Promise.all([
                this.fetchProjectDocuments(),
                this.fetchProjectDocumentTags(),
            ]);
            this.isFetchingContent = false;
        },

        /**
         * Set the selected document state and fetch its child DocumentParts, triggered by
         * clicking a row in the Documents table
         * @param {Object} item Document row object
         */
        async setCurrentDocument(item) {
            this.currentDocument = item;
            this.setDocumentId(item.pk);
            this.isFetchingContent = true;
            await this.fetchDocument();
            this.isFetchingContent = false;
        },

        /**
         * Navigate from the Documents view back to the Projects view
         */
        resetProjectSelection() {
            this.currentProject = null;
        },

        /**
         * Navigate from the Pages grid view back to the Documents view
         */
        async resetDocumentSelection() {
            this.removeFilter("name");
            this.removeFilter("tags");
            this.currentDocument = null;
            if (this.currentProject) {
                this.isFetchingContent = true;
                await this.fetchProjectDocuments();
                this.isFetchingContent = false;
            }
        },

        /**
         * Clear all active navigation layers to return to the root level (Projects view)
         */
        resetAll() {
            this.removeFilter("name");
            this.removeFilter("tags");
            this.currentProject = null;
            this.currentDocument = null;
        },

        /**
         * Remove all staged parts for this document
         * @param {Object} doc Document object
         */
        documentDeselectAll(doc) {
            const docItems = this.collectionItems.filter(
                (i) => i.document_id === doc.pk,
            );
            const pksToRemove = docItems.map((i) => i.document_part);
            pksToRemove.forEach((pk) => this.removeItem(pk));
        },

        /**
         * Toggle the selection state of all parts belonging to a single document
         * @param {Object} doc Document object
         */
        async toggleDocumentSelection(doc) {
            this.isUpdatingSelection = true;
            try {
                if (this.isDocumentFullySelected(doc)) {
                    this.documentDeselectAll(doc);
                } else {
                    // select all: fetch and stage all pages
                    await this.addAllParts({ document: doc });
                }
            } finally {
                this.isUpdatingSelection = false;
            }
        },

        /**
         * Toggle the selection of a single DocumentPart
         * @param {Object} page DocumentPart object
         */
        togglePageSelection(page) {
            if (this.isPageSelected(page.pk)) {
                this.removeItem(page.pk);
            } else {
                this.addSelectedParts({
                    document: this.currentDocument,
                    partPks: [page.pk],
                    partsOverride: [page],
                    transcriptionId: this.defaultTranscription,
                });
            }
        },

        /**
         * Select all DocumentParts on the current document
         */
        async toggleBrowserSelectAll() {
            if (this.currentDocument) {
                await this.toggleDocumentSelection(this.currentDocument);
            }
        },

        /**
         * Deselect all DocumentParts on the current document
         */
        browserDeselectAll() {
            if (this.currentDocument) {
                this.documentDeselectAll(this.currentDocument);
            }
        },

        /**
         * Select or deselect all documents in a project, triggered by the "Select All" checkbox
         * in the Documents table.
         */
        async handleSelectAllDocuments() {
            this.isUpdatingSelection = true;
            try {
                const allSelected = this.storeDocuments.every((doc) =>
                    this.isDocumentFullySelected(doc),
                );
                if (allSelected) {
                    // deselect all: loop through visible docs + remove their parts from collection
                    this.storeDocuments.forEach((doc) => {
                        const itemsToRemove = this.collectionItems.filter(
                            (i) => i.document_id === doc.pk,
                        );
                        itemsToRemove.forEach((item) =>
                            this.removeItem(item.document_part),
                        );
                    });
                } else {
                    // select all: loop through docs and add their parts
                    for (const doc of this.storeDocuments) {
                        if (!this.isDocumentFullySelected(doc)) {
                            await this.addAllParts({ document: doc });
                        }
                    }
                }
            } finally {
                this.isUpdatingSelection = false;
            }
        },

        /**
         * Event handler for toggling a document selection, retrieving the full document
         * object and passing it to the toggle method
         * @param {Event} event The click event (from EscrTable)
         * @param {Number} pk The pk of the document being toggled
         */
        async handleToggleDocument(_, pk) {
            const doc = this.storeDocuments.find((d) => d.pk === pk);
            if (doc) {
                await this.toggleDocumentSelection(doc);
            }
        },

        /**
         * Update the transcription layer for a specific DocumentPart in the collection
         */
        handleUpdateTranscription(page, newTranscriptionId) {
            // we only care if the page is actually selected
            if (this.isPageSelected(page.pk)) {
                this.$store.dispatch("collection/updateItemTranscription", {
                    partPk: page.pk,
                    transcriptionId: parseInt(newTranscriptionId),
                });
            }
        },

        /**
         * Update the default transcription layer for a document
         */
        handleDefaultTranscriptionChange(event) {
            this.$store.dispatch("collection/setDefaultTranscription", {
                documentId: this.currentDocument.pk,
                transcriptionId: parseInt(event.target.value),
            });
        },

        /**
         * Bulk apply the default transcription layer for a document to all its selected parts
         */
        applyDefaultTranscription() {
            const defaultId = this.defaultTranscription;
            if (!defaultId || !this.currentDocument) return;
            const docItems = this.collectionItems.filter(
                (i) => i.document_id === this.currentDocument.pk,
            );
            docItems.forEach((item) => {
                this.$store.dispatch("collection/updateItemTranscription", {
                    partPk: item.document_part,
                    transcriptionId: defaultId,
                });
            });
        },

        /**
         * Re-fetch items when filters are changed
         */
        handleFilter() {
            if (!this.currentProject) {
                this.fetchStoreProjects();
            } else if (!this.currentDocument) {
                this.fetchProjectDocuments();
            } else {
                this.isFetchingContent = true;
                this.fetchParts().finally(() => {
                    this.isFetchingContent = false;
                });
            }
        },

        /**
         * Select all DocumentParts currently visible in the grid
         */
        handleSelectVisible() {
            if (!this.currentDocument || !this.storePages.length) {
                return;
            }
            const unselectedParts = this.storePages.filter(
                (page) => !this.isPageSelected(page.pk)
            );
            if (unselectedParts.length > 0) {
                this.addSelectedParts({
                    document: this.currentDocument,
                    partPks: unselectedParts.map((p) => p.pk),
                    partsOverride: unselectedParts,
                    transcriptionId: this.defaultTranscription,
                });
            }
        },

        /**
         * Load more projects
         */
        async onLoadMoreProjects() {
            this.isFetchingMoreProjects = true;
            await this.fetchNextProjectsPage();
            this.isFetchingMoreProjects = false;
        },

        /**
         * Load more documents
         */
        async onLoadMoreDocuments() {
            this.isFetchingMoreDocuments = true;
            await this.fetchNextDocumentsPage();
            this.isFetchingMoreDocuments = false;
        },

        /**
         * Load more on scroll down (to bottom 50px of tables)
         */
        handleScroll(event) {
            const { scrollTop, clientHeight, scrollHeight } = event.target;
            if (scrollTop + clientHeight >= scrollHeight - 50) {
                // scroll projects
                if (!this.currentProject && !this.currentDocument) {
                    if (this.projectsNextPage && !this.isFetchingMoreProjects && !this.loading) {
                        this.onLoadMoreProjects();
                    }
                }
                // scroll documents
                else if (this.currentProject && !this.currentDocument) {
                    if (
                        this.documentsNextPage &&
                        !this.isFetchingMoreDocuments &&
                        !this.isFetchingContent
                    ) {
                        this.onLoadMoreDocuments();
                    }
                }
            }
        },
    },
};
</script>
