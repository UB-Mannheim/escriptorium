<template>
    <div
        id="elements-panel"
        class="col panel"
    >
        <EditorToolbar
            panel-type="elements"
            :disabled="disabled"
            :panel-index="panelIndex"
        >
            <template #editor-tools-center>
                <div class="escr-editortools-paneltools">
                    <SegmentedButtonGroup
                        color="secondary"
                        name="elements-panel-tab"
                        :disabled="disabled"
                        :options="tabs"
                        :on-change-selection="onSelectTab"
                    />
                    <SegmentedButtonGroup
                        v-if="activeTab === 'lines'"
                        color="secondary"
                        name="elements-panel-identifying-column"
                        :disabled="disabled"
                        :options="identifyingColumnModes"
                        :on-change-selection="onSelectIdentifyingColumnMode"
                    />
                    <div class="escr-elements-filter">
                        <TextField
                            :label-visible="false"
                            label="Filter elements by type, ID, or transcription"
                            placeholder="Filter by type, ID, or transcription"
                            :value="filterText"
                            :on-input="onFilterInput"
                        />
                    </div>
                </div>
            </template>
        </EditorToolbar>
        <div class="content-container">
            <EscrTable
                v-if="items.length"
                item-key="pk"
                compact
                :headers="headers"
                :items="items"
                :disabled="disabled"
                :on-row-click="onSelectElement"
            >
                <template #actions="{ item }">
                    <LockToggle
                        v-if="activeTab === 'regions'"
                        :pk="item.pk"
                        :locked="!!item.locked"
                    />
                    <button
                        v-else
                        type="button"
                        class="escr-elements-edit-button"
                        title="Edit transcription"
                        aria-label="Edit transcription"
                        @click.stop="onEditLine(item)"
                    >
                        <PencilIcon />
                    </button>
                </template>
            </EscrTable>
            <EscrLoader
                v-else
                :loading="false"
                :no-data-message="
                    filterText
                        ? 'No elements match this filter.'
                        : activeTab === 'regions'
                            ? 'There are no regions on this part.'
                            : 'There are no lines on this part.'
                "
            />
        </div>
    </div>
</template>

<script>
import { mapState } from "vuex";
import { BasePanel } from "../../../src/editor/mixins.js";
import EditorToolbar from "../EditorToolbar/EditorToolbar.vue";
import EscrLoader from "../Loader/Loader.vue";
import EscrTable from "../Table/Table.vue";
import LinesIcon from "../Icons/LinesIcon/LinesIcon.vue";
import PencilIcon from "../Icons/PencilIcon/PencilIcon.vue";
import RegionsIcon from "../Icons/RegionsIcon/RegionsIcon.vue";
import SegmentedButtonGroup from "../SegmentedButtonGroup/SegmentedButtonGroup.vue";
import TagIcon from "../Icons/TagIcon/TagIcon.vue";
import TextField from "../TextField/TextField.vue";
import TranscribeIcon from "../Icons/TranscribeIcon/TranscribeIcon.vue";
import LockToggle from "./LockToggle.vue";
import TypeSwatch from "./TypeSwatch.vue";

export default {
    name: "ElementsPanel",
    components: {
        EditorToolbar,
        EscrLoader,
        EscrTable,
        LockToggle,
        PencilIcon,
        SegmentedButtonGroup,
        TextField,
    },
    mixins: [BasePanel],
    data() {
        return {
            // local tab selection; initialized from and kept in sync with the
            // Segmentation panel's current mode, but can be overridden by the user
            activeTab:
                this.$store.state.document.segmentationMode === "regions"
                    ? "regions"
                    : "lines",
            filterText: "",
            // identifying column shown for lines; defaults to transcription content
            identifyingColumnMode: "transcription",
        };
    },
    computed: {
        ...mapState({
            segmentationMode: (state) => state.document.segmentationMode,
            regionColors: (state) => state.document.regionColors,
            allRegions: (state) => state.regions.all,
            allLines: (state) => state.lines.all,
            defaultTextDirection: (state) => state.document.defaultTextDirection,
        }),
        tabs() {
            return [
                {
                    label: RegionsIcon,
                    value: "regions",
                    selected: this.activeTab === "regions",
                    tooltip: "Regions",
                },
                {
                    label: LinesIcon,
                    value: "lines",
                    selected: this.activeTab === "lines",
                    tooltip: "Lines",
                },
            ];
        },
        identifyingColumnModes() {
            const mode = this.identifyingColumnMode;
            return [
                {
                    label: TranscribeIcon,
                    value: "transcription",
                    selected: mode === "transcription",
                    tooltip: "Transcription",
                },
                {
                    label: TagIcon,
                    value: "id",
                    selected: mode === "id",
                    tooltip: "ID",
                },
            ];
        },
        headers() {
            const showTranscription =
                this.activeTab === "lines" && this.identifyingColumnMode === "transcription";
            const identifyingHeader = showTranscription
                ? {
                    label: "Transcription",
                    value: "displayTranscription",
                    class: "escr-elements-identifying-column",
                    dir: this.defaultTextDirection,
                }
                : { label: "ID", value: "displayId", class: "escr-elements-identifying-column" };
            return [
                { label: "Type", value: "typeDisplay", component: TypeSwatch },
                identifyingHeader,
            ];
        },
        items() {
            if (!this.filterText) return this.unfilteredItems;
            const needle = this.filterText.toLowerCase();
            return this.unfilteredItems.filter((item) => (
                item.typeDisplay.name.toLowerCase().includes(needle) ||
                String(item.displayId).toLowerCase().includes(needle) ||
                (item.currentTrans?.content || "").toLowerCase().includes(needle)
            ));
        },
        unfilteredItems() {
            if (this.activeTab === "regions") {
                return this.allRegions.map((region) => ({
                    ...region,
                    displayId: region.external_id || region.pk,
                    typeDisplay: {
                        name: region.type || "None",
                        color: this.regionColors[region.type || "None"] || "#808080",
                    },
                }));
            }
            // lines: show in reading order, colored by their parent region
            return this.allLines
                .slice()
                .sort((a, b) => a.order - b.order)
                .map((line) => {
                    const region = this.allRegions.find((r) => r.pk === line.region);
                    const transcription = line.currentTrans?.content || "";
                    return {
                        ...line,
                        displayId: line.external_id || line.pk,
                        displayTranscription: transcription.length > 20
                            ? `${transcription.slice(0, 20)}…`
                            : transcription,
                        typeDisplay: {
                            name: line.type || "None",
                            color: region
                                ? this.regionColors[region.type || "None"] || "#808080"
                                : null,
                            gradient: !region,
                        },
                    };
                });
        },
    },
    watch: {
        // auto-follow the Segmentation panel's mode (masks counts as "lines")
        segmentationMode(mode) {
            this.activeTab = mode === "regions" ? "regions" : "lines";
        },
    },
    methods: {
        onSelectTab(tab) {
            this.activeTab = tab;
            this.$store.commit("document/setSegmentationMode", tab);
        },
        onFilterInput(e) {
            this.filterText = e.target.value;
        },
        onSelectIdentifyingColumnMode(mode) {
            this.identifyingColumnMode = mode;
        },
        onSelectElement(item) {
            const mutation = this.activeTab === "regions" ? "regions/setSelected" : "lines/setSelected";
            this.$store.commit(mutation, item.pk);
        },
        onEditLine(item) {
            this.$store.dispatch("lines/toggleLineEdition", item);
        },
        updateView() {},
    },
};
</script>

<style scoped>
.escr-elements-filter {
    flex: 1 0 auto;
}

.content-container {
    overflow-y: auto;
    overflow-x: hidden;
}

.escr-elements-edit-button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: none;
    border: none;
    padding: 0.2rem;
    cursor: pointer;
    color: inherit;
}

.escr-elements-edit-button:hover {
    color: var(--secondary);
}
</style>

<style>
/* tighter rows than the default compact table, to fit more elements per panel */
#elements-panel .escr-table--compact tbody tr {
    height: 32px;
}

/* space out the tab switcher, identifying-column toggle, and filter in the toolbar */
#elements-panel .escr-editortools-paneltools {
    gap: 0.75rem;
}

/* the lock/edit action should always be visible here, not just on row hover/focus */
#elements-panel .escr-table td.escr-row-actions * {
    opacity: 1;
}

/* breathing room between columns, which otherwise sit flush against each other */
#elements-panel .escr-table th,
#elements-panel .escr-table td {
    padding-right: 0.75rem;
}

/* truncate long transcription/ID content instead of wrapping or overflowing the row */
#elements-panel .escr-table td.escr-elements-identifying-column {
    max-width: 0;
    width: 100%;
}
#elements-panel .escr-table td.escr-elements-identifying-column span {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
</style>
