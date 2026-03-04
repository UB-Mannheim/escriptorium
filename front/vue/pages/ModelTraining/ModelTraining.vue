<template>
    <EscrPage class="escr-model-training">
        <template #page-content>
            <h1>Model Training</h1>
            <!-- collection management -->
            <section class="escr-collection-management">
                <h2>Manage Collection</h2>
                <div
                    class="escr-card escr-card-padding escr-collection-actions"
                >
                    <!-- name -->
                    <div class="escr-collection-name">
                        <h3
                            v-if="!isEditingName"
                            @click="isEditingName = true"
                        >
                            <span>{{ collectionName || "Untitled Collection" }}</span>
                            <PencilIcon />
                        </h3>
                        <div
                            v-else
                            class="escr-collection-name-editor"
                        >
                            <EscrTextField
                                ref="nameInput"
                                class="escr-collection-name-input"
                                name="virtual-collection-name"
                                label="Collection Name"
                                :label-visible="false"
                                placeholder="Name your collection..."
                                :value="collectionName"
                                :on-input="handleNameChange"
                                :on-blur="() => { isEditingName = false; }"
                                :on-keydown="handleNameKeydown"
                                :max-length="512"
                            />
                            <EscrButton
                                color="outline-primary"
                                :on-click="() => { isEditingName = false; }"
                                @mousedown.native.prevent="isEditingName = false"
                            >
                                <template #button-icon>
                                    <CheckIcon />
                                </template>
                            </EscrButton>
                        </div>
                    </div>
                    <!-- collection select dropdown -->
                    <div class="escr-collection-dropdown">
                        <EscrDropdownField
                            label="Load Collection:"
                            :label-visible="true"
                            :options="collectionsOptions"
                            :on-change="handleLoadCollection"
                        />
                        <EscrButton
                            :disabled="!collectionId"
                            label="Start New"
                            color="outline-primary"
                            :on-click="handleNewCollection"
                            size="small"
                        />
                    </div>
                    <!-- images count and save -->
                    <div
                        class="escr-card escr-card-padding escr-save-collection"
                    >
                        <span>
                            <strong>{{ collectionItems.length }}</strong> elements
                            staged for model training.
                        </span>
                        <EscrButton
                            label="Save Collection"
                            color="primary"
                            :disabled="
                                isSavingCollection ||
                                    !collectionName ||
                                    collectionItems.length === 0
                            "
                            :on-click="handleSaveCollection"
                        />
                    </div>
                </div>
            </section>
            <!-- browser to populate training data -->
            <section>
                <h2>Browse</h2>
                <EscriptoriumBrowser />
            </section>
        </template>
    </EscrPage>
</template>
<script>
import { mapActions, mapState } from "vuex";
import EscrPage from "../Page/Page.vue";
import EscrButton from "../../components/Button/Button.vue";
import EscrDropdownField from "../../components/Dropdown/DropdownField.vue";
import EscrTextField from "../../components/TextField/TextField.vue";
import EscriptoriumBrowser from "../../components/EscriptoriumBrowser/EscriptoriumBrowser.vue";
import PencilIcon from "../../components/Icons/PencilIcon/PencilIcon.vue";
import CheckIcon from "../../components/Icons/CheckIcon/CheckIcon.vue";
import "../../components/Common/Card.css";
import "./ModelTraining.css";

export default {
    name: "EscrModelTrainingPage",
    components: {
        CheckIcon,
        EscrPage,
        EscrButton,
        EscrDropdownField,
        EscrTextField,
        EscriptoriumBrowser,
        PencilIcon,
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
            isEditingName: false,
        };
    },
    computed: {
        ...mapState("collection", {
            collections: (state) => state.collections,
            collectionId: (state) => state.currentCollection.id,
            collectionName: (state) => state.currentCollection.name,
            collectionItems: (state) => state.currentCollection.items,
            isSavingCollection: (state) => state.loading,
        }),
        /**
         * The user's collections, formatted for the dropdown
         */
        collectionsOptions() {
            return this.collections.map((c) => ({
                value: String(c.id),
                label: c.name,
                selected: c.id === this.collectionId,
            }));
        },
    },
    mounted() {
        this.$store.dispatch("collection/fetchCollections");
    },
    methods: {
        ...mapActions("collection", ["saveCollection", "loadCollection"]),
        /**
         * Handler for clicking the pencil icon to edit the collection name
         */
        startEditingName() {
            this.isEditingName = true;
            this.$nextTick(() => {
                const input = this.$refs.nameInput?.$el?.querySelector("input");
                if (input) {
                    input.focus();
                }
            });
        },
        /**
         * Update the collection name on state
         */
        handleNameChange(event) {
            this.$store.commit(
                "collection/setCollectionName",
                event.target.value,
            );
        },
        /**
         * Stop editing name on Enter key
         */
        handleNameKeydown(event) {
            if (event.key === "Enter") {
                event.preventDefault();
                this.isEditingName = false;
            }
        },
        /**
         * Persist the collection in the backend
         */
        async handleSaveCollection() {
            try {
                await this.saveCollection();
                this.$store.dispatch("alerts/add", {
                    color: "success",
                    message: "Collection saved successfully!",
                });
            } catch (error) {
                this.$store.dispatch("alerts/addError", error);
            }
        },
        /**
         * Load a collection from the backend
         */
        handleLoadCollection(event) {
            this.loadCollection(event.target.value);
            this.isEditingName = false;
        },
        /**
         * Reset the collection state to empty
         */
        handleNewCollection() {
            this.loadCollection(null);
            this.isEditingName = false;
        },
    },
};
</script>
