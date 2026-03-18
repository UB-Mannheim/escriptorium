<template>
    <div class="escr-card escr-card-padding escr-collection-actions">
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
        <!-- name -->
        <div class="escr-collection-name">
            <h3
                v-if="!isEditingName"
                @click="startEditingName"
            >
                <span>
                    {{ collectionName || "Untitled Collection" }}
                    {{ isDirty ? "*" : "" }}
                </span>
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
        <!-- images count and save -->
        <div class="escr-save-collection">
            <span class="collection-stats">
                <strong>{{ collectionItems.length }}</strong> parts staged
            </span>
            <EscrButton
                label="Save Collection"
                color="primary"
                :disabled="
                    isLoadingCollection ||
                        isSavingCollection ||
                        collectionItems.length === 0 ||
                        !isDirty
                "
                :on-click="handleSaveCollection"
            />
        </div>
    </div>
</template>

<script>
import { mapActions, mapState } from "vuex";
import EscrButton from "../../components/Button/Button.vue";
import EscrDropdownField from "../../components/Dropdown/DropdownField.vue";
import EscrTextField from "../../components/TextField/TextField.vue";
import PencilIcon from "../../components/Icons/PencilIcon/PencilIcon.vue";
import CheckIcon from "../../components/Icons/CheckIcon/CheckIcon.vue";
import "./ManageCollectionForm.css";

export default {
    name: "ManageCollectionForm",
    components: {
        CheckIcon,
        EscrButton,
        EscrDropdownField,
        EscrTextField,
        PencilIcon,
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
            isLoadingCollection: (state) => state.loading,
            isSavingCollection: (state) => state.saving,
            isDirty: (state) => state.dirty,
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
            // If the user hasn't set a name, default it to "Untitled Collection"
            if (!this.collectionName || this.collectionName.trim() === "") {
                this.$store.commit(
                    "collection/setCollectionName",
                    "Untitled Collection",
                );
            }
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
         * Load a collection from the backend, prompting user on unsaved
         * changes, and loading the selected parts tab
         */
        handleLoadCollection(event) {
            if (this.isDirty) {
                const confirmDiscard = window.confirm(
                    "You have unsaved changes in your current collection. " +
                    "Are you sure you want to load a new one and discard these changes?"
                );
                if (!confirmDiscard) {
                    return;
                }
            }
            this.loadCollection(event.target.value);
            this.isEditingName = false;
            // send parent to "selected" tab
            this.$emit("loaded");
        },
        /**
         * Reset the collection state to empty, prompting user on unsaved
         * changes, and loading the browse tab
         */
        handleNewCollection() {
            if (this.isDirty) {
                const confirmDiscard = window.confirm(
                    "You have unsaved changes in your current collection. " +
                    "Are you sure you want to start a new one and discard these changes?"
                );
                if (!confirmDiscard) {
                    return;
                }
            }
            this.loadCollection(null);
            this.isEditingName = false;
            // send parent to "browse" tab
            this.$emit("new-started");
        },
    },
};
</script>
