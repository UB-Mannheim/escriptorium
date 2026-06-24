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
                </div>
            </template>
        </EditorToolbar>
        <div class="escr-elements-filter">
            <TextField
                :label-visible="false"
                label="Filter elements by type or ID"
                placeholder="Filter by type or ID"
                :value="filterText"
                :on-input="onFilterInput"
            />
        </div>
        <div class="content-container">
            <EscrTable
                v-if="items.length"
                item-key="pk"
                compact
                :headers="headers"
                :items="items"
                :disabled="disabled"
                :on-row-click="onSelectElement"
            />
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
import SegmentedButtonGroup from "../SegmentedButtonGroup/SegmentedButtonGroup.vue";
import TextField from "../TextField/TextField.vue";
import LockToggle from "./LockToggle.vue";
import TypeSwatch from "./TypeSwatch.vue";

export default {
    name: "ElementsPanel",
    components: { EditorToolbar, EscrLoader, EscrTable, SegmentedButtonGroup, TextField },
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
        };
    },
    computed: {
        ...mapState({
            segmentationMode: (state) => state.document.segmentationMode,
            regionColors: (state) => state.document.regionColors,
            allRegions: (state) => state.regions.all,
            allLines: (state) => state.lines.all,
        }),
        tabs() {
            return [
                { label: "Regions", value: "regions", selected: this.activeTab === "regions" },
                { label: "Lines", value: "lines", selected: this.activeTab === "lines" },
            ];
        },
        headers() {
            const headers = [
                { label: "Type", value: "typeDisplay", component: TypeSwatch },
                { label: "ID", value: "displayId" },
            ];
            if (this.activeTab === "regions") {
                headers.push({ label: "Lock", value: "lockToggle", component: LockToggle });
            }
            return headers;
        },
        items() {
            if (!this.filterText) return this.unfilteredItems;
            const needle = this.filterText.toLowerCase();
            return this.unfilteredItems.filter((item) => (
                item.typeDisplay.name.toLowerCase().includes(needle) ||
                String(item.displayId).toLowerCase().includes(needle)
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
                    lockToggle: {
                        pk: region.pk,
                        locked: !!region.locked,
                    },
                }));
            }
            // lines: show in reading order, colored by their parent region
            return this.allLines
                .slice()
                .sort((a, b) => a.order - b.order)
                .map((line) => {
                    const region = this.allRegions.find((r) => r.pk === line.region);
                    return {
                        ...line,
                        displayId: line.external_id || line.pk,
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
        },
        onFilterInput(e) {
            this.filterText = e.target.value;
        },
        onSelectElement(item) {
            const mutation = this.activeTab === "regions" ? "regions/setSelected" : "lines/setSelected";
            this.$store.commit(mutation, item.pk);
        },
        updateView() {},
    },
};
</script>

<style scoped>
.escr-elements-filter {
    padding: 0.5rem 0.75rem;
}

.content-container {
    overflow-y: auto;
    overflow-x: hidden;
}
</style>

<style>
/* tighter rows than the default compact table, to fit more elements per panel */
#elements-panel .escr-table--compact tbody tr {
    height: 32px;
}
</style>
