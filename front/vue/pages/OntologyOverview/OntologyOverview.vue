<template>
    <EscrPage
        class="escr-ontology-overview-page"
        :breadcrumbs="breadcrumbs"
        :loading="loading"
    >
        <template #page-content>
            <div class="escr-container">
                <div class="escr-ontology-overview-header">
                    <h3 :title="documentName">
                        {{ documentName || "Loading..." }}
                    </h3>
                    <h1>Ontology Overview</h1>
                </div>
                <div class="escr-ontology-overview-controls">
                    <SegmentedButtonGroup
                        color="secondary"
                        name="ontology-overview-category"
                        :disabled="loading"
                        :options="categories"
                        :on-change-selection="onSelectCategory"
                    />
                    <div
                        v-if="category === 'characters'"
                        class="escr-ontology-overview-transcription"
                    >
                        <h3>Transcription:</h3>
                        <EscrDropdown
                            label="Change the transcription used for character stats"
                            :disabled="loading"
                            :options="transcriptionLevels"
                            :on-change="onSelectTranscription"
                        />
                    </div>
                </div>
                <div
                    v-if="loading"
                    class="escr-ontology-overview-loading"
                >
                    <EscrLoader
                        :loading="true"
                        no-data-message=""
                    />
                </div>
                <div
                    v-else
                    class="escr-ontology-overview-body"
                >
                    <div class="escr-ontology-overview-types">
                        <h2>
                            {{ typesHeading }}
                        </h2>
                        <EscrTable
                            v-if="types.length"
                            item-key="key"
                            compact
                            :headers="typeHeaders"
                            :items="types"
                            :on-row-click="onSelectType"
                        />
                        <EscrLoader
                            v-else
                            :loading="false"
                            no-data-message="There is no ontology to display."
                        />
                    </div>
                    <div class="escr-ontology-overview-parts">
                        <template v-if="selectedType">
                            <h2>
                                Parts containing "{{ selectedType.name }}"
                            </h2>
                            <EscrTable
                                v-if="selectedTypeParts.length"
                                item-key="document_part_id"
                                compact
                                linkable
                                :headers="partHeaders"
                                :items="selectedTypeParts"
                                :disabled="selectedTypeLoading"
                            />
                            <EscrLoader
                                v-else
                                :loading="selectedTypeLoading"
                                no-data-message="This type is not used in any part."
                            />
                        </template>
                        <p v-else>
                            Select a type to see which parts contain it.
                        </p>
                    </div>
                </div>
            </div>
        </template>
    </EscrPage>
</template>
<script>
import { mapActions, mapState } from "vuex";
import { SCRIPT_NAME } from "../../../src/scriptname.js";
import EscrDropdown from "../../components/Dropdown/Dropdown.vue";
import EscrLoader from "../../components/Loader/Loader.vue";
import EscrPage from "../Page/Page.vue";
import EscrTable from "../../components/Table/Table.vue";
import SegmentedButtonGroup from "../../components/SegmentedButtonGroup/SegmentedButtonGroup.vue";
import "./OntologyOverview.css";

export default {
    name: "EscrOntologyOverview",
    components: { EscrDropdown, EscrLoader, EscrPage, EscrTable, SegmentedButtonGroup },
    props: {
        /**
         * The primary key/id of the current document.
         */
        documentId: {
            type: Number,
            required: true,
        },
    },
    data() {
        return {
            category: "regions",
            selectedType: null,
            // true while the document's ontology stats are being force-refreshed on load
            refreshingStats: true,
        };
    },
    computed: {
        ...mapState({
            documentName: (state) => state.document.name,
            projectName: (state) => state.document.projectName,
            projectSlug: (state) => state.document.projectSlug,
            validTypes: (state) => state.document.types,
            transcriptions: (state) => state.document.transcriptions,
            characters: (state) => state.characters.characters,
            selectedTranscription: (state) => state.transcription.selectedTranscription,
            partsByType: (state) => state.ontology.partsByType,
            partsByChar: (state) => state.ontology.partsByChar,
            documentLoading: (state) => state.document.loading?.document,
        }),
        loading() {
            return !!this.documentLoading || this.refreshingStats;
        },
        breadcrumbs() {
            let docBreadcrumbs = [{ title: "Loading..." }, { title: "Loading..." }];
            if (this.projectName && this.projectSlug && this.documentName) {
                docBreadcrumbs = [
                    { title: this.projectName, href: SCRIPT_NAME + `/project/${this.projectSlug}/` },
                    { title: this.documentName, href: SCRIPT_NAME + `/document/${this.documentId}/` },
                ];
            }
            return [
                { title: "My Projects", href: SCRIPT_NAME + "/projects/" },
                ...docBreadcrumbs,
                { title: "Ontology Overview" },
            ];
        },
        categories() {
            return [
                { label: "Regions", value: "regions" },
                { label: "Lines", value: "lines" },
                { label: "Text Annotations", value: "text" },
                { label: "Image Annotations", value: "image" },
                { label: "Characters", value: "characters" },
            ].map((category) => ({
                ...category,
                selected: this.category === category.value,
            }));
        },
        transcriptionLevels() {
            return (this.transcriptions || []).map((transcription) => ({
                value: transcription.pk,
                selected: parseInt(this.selectedTranscription) === parseInt(transcription.pk),
                label: transcription.name,
            }));
        },
        types() {
            let items;
            if (this.category === "characters") {
                items = (this.characters || []).map((c) => ({
                    ...c,
                    name: this.displayChar(c.char),
                    key: `characters-${c.char}`,
                }));
            } else if (!this.validTypes || !this.validTypes[this.category]) {
                items = [];
            } else {
                items = this.validTypes[this.category].map((type) => ({
                    ...type,
                    key: `${this.category}-${type.typology_id ?? "none"}`,
                }));
            }
            return items.slice().sort((a, b) => b.frequency - a.frequency);
        },
        typesHeading() {
            const headings = {
                regions: "Region Types",
                lines: "Line Types",
                text: "Text Annotation Types",
                image: "Image Annotation Types",
                characters: "Characters",
            };
            return headings[this.category] || "Types";
        },
        typeHeaders() {
            return [
                {
                    label: this.category === "characters" ? "Character" : "Type",
                    value: "name",
                    sortable: false,
                },
                { label: "# in Document", value: "frequency", sortable: false },
            ];
        },
        partHeaders() {
            return [
                { label: "Part", value: "part_name" },
                { label: "# on Part", value: "frequency" },
            ];
        },
        selectedTypeKey() {
            if (!this.selectedType) return null;
            if (this.category === "characters") return this.selectedType.char;
            return `${this.category}-${this.selectedType.typology_id ?? "none"}`;
        },
        selectedTypeParts() {
            if (!this.selectedTypeKey) return [];
            const byKey = this.category === "characters" ? this.partsByChar : this.partsByType;
            const parts = byKey[this.selectedTypeKey]?.parts || [];
            return parts.map((part) => ({
                ...part,
                part_name: part.part_name || part.part_filename || "Untitled",
                href: `/document/${this.documentId}/part/${part.document_part_id}/edit/`,
            }));
        },
        selectedTypeLoading() {
            if (!this.selectedTypeKey) return false;
            const byKey = this.category === "characters" ? this.partsByChar : this.partsByType;
            return !!byKey[this.selectedTypeKey]?.loading;
        },
    },
    async created() {
        this.setId(this.documentId);
        try {
            await this.fetchDocument();
            // force-refresh the cached ontology stats so newly imported data shows up immediately
            await this.fetchDocumentStats({ refresh: true });
            if (this.selectedTranscription) {
                await this.fetchTranscriptionStats();
            }
        } catch (error) {
            this.addError(error);
        } finally {
            this.refreshingStats = false;
        }
    },
    methods: {
        ...mapActions("alerts", ["addError"]),
        ...mapActions("document", [
            "setId",
            "changeSelectedTranscription",
            "fetchDocument",
            "fetchDocumentStats",
            "fetchTranscriptionStats",
        ]),
        ...mapActions("ontology", ["fetchElementsByType", "fetchPartsByChar"]),
        onSelectCategory(category) {
            this.category = category;
            this.selectedType = null;
        },
        async onSelectTranscription(e) {
            this.selectedType = null;
            await this.changeSelectedTranscription(parseInt(e.target.value, 10));
        },
        async onSelectType(type) {
            this.selectedType = type;
            if (this.category === "characters") {
                await this.fetchPartsByChar({
                    char: type.char,
                    transcriptionId: this.selectedTranscription,
                });
            } else {
                await this.fetchElementsByType({
                    category: this.category,
                    typePk: type.typology_id,
                });
            }
        },
        /**
         * Render whitespace characters in a readable way
         */
        displayChar(char) {
            if (char === " ") return "(space)";
            if (char === "\n") return "\\n";
            return char;
        },
    },
};
</script>
