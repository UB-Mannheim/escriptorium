<template>
    <EscrPage class="escr-model-training">
        <template #page-content>
            <h1 v-translate>Model Training</h1>
            <div class="escr-training-container">
                <div class="escr-training-collections">
                    <div class="escr-training-data">
                        <EscrTabs
                            v-model="activeTab"
                            :tabs="trainingDataTabs"
                        />
                        <div class="escr-tab-content">
                            <!-- browser to populate training data -->
                            <div
                                v-show="activeTab === 'browse'"
                                id="panel-browse"
                                class="escr-tab-panel"
                                role="tabpanel"
                                aria-labelledby="tab-browse"
                                tabindex="0"
                            >
                                <h2 class="sr-only" v-translate>
                                    Browse
                                </h2>
                                <EscriptoriumBrowser
                                    v-if="escrBrowserLoaded"
                                    :preselected-project="preselectedProject"
                                    :preselected-document="preselectedDocument"
                                />
                                <div
                                    v-else
                                    class="escr-spinner escr-spinner--secondary"
                                    role="status"
                                >
                                    <span class="sr-only">{{ $gettext("Loading browser...") }}</span>
                                </div>
                            </div>
                            <!-- selected documents expand/collapse section -->
                            <div
                                v-show="activeTab === 'selected'"
                                id="panel-selected"
                                class="escr-tab-panel escr-selected-parts"
                                role="tabpanel"
                                aria-labelledby="tab-selected"
                                tabindex="0"
                            >
                                <h2 class="sr-only" v-translate>
                                    Selected Documents and Parts
                                </h2>
                                <div
                                    v-if="isLoadingCollection"
                                    class="escr-spinner escr-spinner--secondary"
                                    role="status"
                                >
                                    <span class="sr-only">{{ $gettext("Loading collection...") }}</span>
                                </div>
                                <SelectedDocuments v-else-if="collectionItems.length" />
                                <div
                                    v-else
                                    class="escr-card escr-card-padding"
                                >
                                    <p v-translate>No parts currently selected.</p>
                                    <p v-translate>Load a saved collection, or navigate to the Browse tab.</p>
                                    <EscrButton
                                        :label="$gettext('Browse')"
                                        color="outline-primary"
                                        :on-click="() => activeTab = 'browse'"
                                    />
                                </div>
                            </div>
                        </div>
                    </div>
                    <!-- collection management -->
                    <aside class="escr-training-sidebar">
                        <section class="escr-collection-management">
                            <h2 v-translate>Manage Collection</h2>
                            <ManageCollectionForm
                                @loaded="activeTab = 'selected'"
                                @new-started="activeTab = 'browse'"
                            />
                        </section>
                    </aside>
                </div>
                <!-- model training form -->
                <section class="escr-training-footer">
                    <h2 v-translate>Train Model</h2>
                    <TrainForm />
                </section>
            </div>
        </template>
    </EscrPage>
</template>
<script>
import { mapActions, mapState } from "vuex";
import EscrPage from "../Page/Page.vue";
import EscrButton from "../../components/Button/Button.vue";
import EscrTabs from "../../components/Tabs/Tabs.vue";
import EscriptoriumBrowser from "../../components/EscriptoriumBrowser/EscriptoriumBrowser.vue";
import ManageCollectionForm from "../../components/ManageCollectionForm/ManageCollectionForm.vue";
import SelectedDocuments from "../../components/EscriptoriumBrowser/SelectedDocuments.vue";
import TrainForm from "../../components/TrainForm/TrainForm.vue";
import "../../components/Common/Card.css";
import "./ModelTraining.css";

export default {
    name: "EscrModelTrainingPage",
    components: {
        EscrButton,
        EscrPage,
        EscrTabs,
        EscriptoriumBrowser,
        ManageCollectionForm,
        SelectedDocuments,
        TrainForm,
    },
    props: {
        /**
         * Whether or not search is disabled on the current instance.
         */
        searchDisabled: {
            type: Boolean,
            required: true,
        },
    },
    data() {
        return {
            activeTab: "browse",
            preselectedProject: null,
            preselectedDocument: null,
            escrBrowserLoaded: false,
        };
    },
    computed: {
        ...mapState("collection", {
            collectionItems: (state) => state.currentCollection.items,
            isLoadingCollection: (state) => state.loading,
            isDirty: (state) => state.dirty,
        }),
        /**
         * tabs for training data management, with parts count as badges
         */
        trainingDataTabs() {
            return [
                { label: this.$gettext("Browse"), value: "browse" },
                {
                    label: this.$gettext("Selected Documents and Parts"),
                    value: "selected",
                    badge: this.collectionItems.length
                },
            ];
        }
    },
    async mounted() {
        // fetch all collections
        await this.$store.dispatch("collection/fetchCollections");

        // grab preselected parts/project/doc data from session storage
        const preselected = sessionStorage.getItem("escr-training-data");
        if (preselected) {
            // load parts and document from preselected
            const data = JSON.parse(preselected);
            this.preselectedProject = data.project;
            this.preselectedDocument = data.document;
            await this.loadCollection(null);
            await this.$store.dispatch("collection/addSelectedParts", {
                document: this.preselectedDocument,
                partPks: data.selectedParts,
                partsOverride: data.parts,
            });
            // remove the keys from session storage
            sessionStorage.removeItem("escr-training-data");
            this.activeTab = "selected";
        } else if (this.collectionItems.length > 0) {
            this.activeTab = "selected";
        }
        this.escrBrowserLoaded = true;

        // add beforeunload event handler to show "unsaved changes" prompt
        window.addEventListener("beforeunload", this.handleBeforeUnload);
    },
    beforeDestroy() {
        // clean up beforeunload listener
        window.removeEventListener("beforeunload", this.handleBeforeUnload);
    },
    methods: {
        ...mapActions("collection", ["loadCollection"]),
        /**
         * Intercept browser navigation/close if there are unsaved changes
         */
        handleBeforeUnload(event) {
            if (this.isDirty) {
                event.preventDefault();
                // Chrome requires returnValue to trigger the warning prompt
                event.returnValue = "";
            }
        },
    },
};
</script>
