<template>
    <div :class="classes">
        <div class="escr-card-header">
            <h2>
                Ontology
            </h2>
            <div class="escr-card-actions">
                <SegmentedButtonGroup
                    v-if="compact"
                    color="secondary"
                    name="ontology-category"
                    :disabled="loading"
                    :options="categories"
                    :on-change-selection="onSelectCategory"
                />
            </div>
        </div>
        <SegmentedButtonGroup
            v-if="!compact"
            color="secondary"
            name="ontology-category"
            :disabled="loading"
            :options="categories"
            :on-change-selection="onSelectCategory"
        />
        <div
            v-if="items && items.length"
            class="escr-ontology-table-container"
        >
            <EscrTable
                item-key="typology_id"
                compact
                :headers="tableHeaders"
                :items="items"
                :on-sort="onSort"
                :disabled="loading"
            />
        </div>
        <EscrLoader
            v-else
            :loading="loading"
            no-data-message="There is no ontology to display."
        />
    </div>
</template>
<script>
import { mapState } from "vuex";
import EscrLoader from "../Loader/Loader.vue";
import EscrTable from "../Table/Table.vue";
import SegmentedButtonGroup from "../SegmentedButtonGroup/SegmentedButtonGroup.vue";
import "./OntologyCard.css";

export default {
    name: "EscrOntologyCard",
    components: { EscrLoader, EscrTable, SegmentedButtonGroup },
    props: {
        /**
         * Whether or not to display a compact variant of this card (i.e. for document view).
         */
        compact: {
            type: Boolean,
            default: false,
        },
        /**
         * Boolean indicating whether or not data is loading.
         */
        loading: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        return {
            // should be one of regions, lines, text, image
            category: "regions",
            sort: null,
        }
    },
    computed: {
        ...mapState({
            validTypes: (state) => state.document.types,
        }),
        /**
         * Mapping of ontology categories to label/value pairs, passing the `selected` prop to the
         * currently selected one.
         */
        categories() {
            return [
                { label: "Regions", value: "regions" },
                { label: "Lines", value: "lines" },
                { label: "Text", value: "text" },
                { label: "Images", value: "image" },
            ].map((category) => ({
                ...category,
                selected: this.category === category.value,
            }));
        },
        /**
         * Apply the compact class if needed
         */
        classes() {
            return {
                "escr-card": true,
                "escr-card-table": true,
                "escr-ontology-card": true,
                "escr-ontology-card--compact": this.compact,
            };
        },
        /**
         * Get the list of items for the selected category and apply any sort
         */
        items() {
            if (this.validTypes && this.category) {
                let items = this.validTypes[this.category];
                if (items && this.sort) {
                    // case insensitive sort
                    return items.toSorted(
                        (a, b) => {
                            let afield = a[this.sort.field];
                            let bfield = b[this.sort.field];
                            if (typeof afield === "string") {
                                afield = afield.toLowerCase();
                                bfield = bfield.toLowerCase();
                            }
                            if (afield < bfield) {
                                return -1 * this.sort.direction;
                            }
                            if (afield > bfield) {
                                return this.sort.direction;
                            }
                            return 0;
                        }
                    );
                }
                return items;
            }
            return [];
        },
        /**
         * Headers for all ontology tables (type, # in document).
         */
        tableHeaders() {
            return [
                { label: "Type", value: "name", sortable: true },
                { label: "# in Document", value: "frequency", sortable: true },
            ];
        },
    },
    methods: {
        /**
         * Callback for changing the category on component state
         */
        onSelectCategory(category) {
            this.category = category;
        },
        /**
         * Callback for changing the component sort state
         */
        onSort(sort) {
            if (sort.direction === 0) {
                this.sort = null;
            } else {
                this.sort = sort;
            }
        },
    },
}
</script>
