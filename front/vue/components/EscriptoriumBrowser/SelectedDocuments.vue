<template>
    <div class="selected-documents-container">
        <div class="document-chips">
            <button
                v-for="doc in groupedDocs"
                :key="`doc-${doc.id}`"
                class="doc-expand"
                :class="{
                    active: expandedFolderId === doc.id,
                }"
                :disabled="loadingFolderId === doc.id"
                @click="toggleFolder(doc.id)"
            >
                {{ doc.name }} ({{ doc.items.length }})
                <div
                    v-if="loadingFolderId === doc.id"
                    class="escr-spinner"
                    role="status"
                />
                <ChevronUpIcon v-if="expandedFolderId === doc.id" />
                <ChevronDownLargeIcon v-else />
            </button>
        </div>

        <div
            v-if="expandedFolderId !== null"
            class="folders-wrapper"
        >
            <div
                v-for="doc in groupedDocs"
                v-show="expandedFolderId === doc.id"
                :key="`folder-${doc.id}`"
                class="folder-group"
            >
                <div
                    class="folder-tab"
                    @click="toggleFolder(doc.id)"
                >
                    <span><strong>{{ doc.name }}</strong> ({{
                        doc.items.length
                    }}
                        parts)</span>
                    <XIcon />
                </div>

                <div class="folder-content">
                    <div class="selected-parts-grid">
                        <div
                            v-for="part in doc.items"
                            :key="part.document_part"
                            class="selected-part-card"
                        >
                            <button
                                class="remove-part-btn"
                                aria-label="Remove part"
                                @click="removeSelectedPart(part.document_part)"
                            >
                                &times;
                            </button>
                            <div class="part-thumbnail">
                                <img
                                    :src="getThumbnailUrl(part)"
                                    alt="thumbnail"
                                    loading="lazy"
                                >
                            </div>
                            <!-- filename with tooltip for overflow -->
                            <VDropdown
                                placement="bottom"
                                :triggers="['hover']"
                                theme="escr-tooltip-small"
                                class="filename"
                            >
                                <span>
                                    {{ part.part_order + 1 }}
                                    &ndash;
                                    {{ part.part_name || `Page ${part.document_part}` }}
                                </span>
                                <template #popper>
                                    {{ part.part_name || `Page ${part.document_part}` }}
                                </template>
                            </VDropdown>
                            <div class="part-actions">
                                <select
                                    class="transcription-select"
                                    :value="getPartLayerId(part, doc)"
                                    @change="(e) => updateTranscription(part, e.target.value)"
                                >
                                    <option
                                        v-for="opt in doc.baseTransOpts"
                                        :key="opt.value"
                                        :value="opt.value"
                                    >
                                        {{ opt.label }}
                                    </option>
                                </select>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import { mapState, mapActions } from "vuex";
import { Dropdown as VDropdown } from "floating-vue";
import ChevronDownLargeIcon from "../Icons/ChevronDownLargeIcon/ChevronDownLargeIcon.vue";
import ChevronUpIcon from "../Icons/ChevronUpIcon/ChevronUpIcon.vue";
import XIcon from "../Icons/XIcon/XIcon.vue";
import "./SelectedDocuments.css";

export default {
    name: "SelectedDocuments",
    components: {
        ChevronDownLargeIcon,
        ChevronUpIcon,
        XIcon,
        VDropdown,
    },
    data() {
        return {
            expandedFolderId: null,
            loadingFolderId: null,
        };
    },
    computed: {
        ...mapState("collection", {
            collectionItems: (state) => state.currentCollection.items,
            documentTranscriptions: (state) => state.documentTranscriptions,
        }),
        ...mapState("project", {
            storeDocuments: "documents",
        }),

        /**
         * group document parts by document
         */
        groupedDocs() {
            if (!this.collectionItems || this.collectionItems.length === 0) {
                return [];
            }

            // store in object keyed on doc id
            const groups = {};
            this.collectionItems.forEach((item) => {
                const docId = item.document_id;

                if (!groups[docId]) {
                    const storeDoc = this.storeDocuments.find(
                        (d) => d.pk === docId,
                    );

                    const rawTranscriptions =
                        storeDoc?.transcriptions ||
                        this.documentTranscriptions[docId] ||
                        [];

                    // build the transcription options array once per document
                    const baseTransOpts = rawTranscriptions.map((t) => ({
                        value: String(t.id || t.pk),
                        label: t.name,
                    }));

                    groups[docId] = {
                        id: docId,
                        name: item.document_name,
                        baseTransOpts,
                        items: [],
                    };
                }

                groups[docId].items.push(item);
            });

            return Object.values(groups).map((group) => {
                // sort by order on the document
                group.items.sort((a, b) => {
                    const orderA = a.part_order !== undefined ? a.part_order : a.document_part;
                    const orderB = b.part_order !== undefined ? b.part_order : b.document_part;
                    return orderA - orderB;
                });
                return group;
            });
        },
    },
    watch: {
        groupedDocs: {
            deep: true,
            handler(newGroups, oldGroups) {
                if (newGroups.length > (oldGroups ? oldGroups.length : 0)) {
                    const newDoc = newGroups.find(
                        (g) =>
                            !(oldGroups || []).some((old) => old.id === g.id),
                    );
                    if (newDoc && this.expandedFolderId !== newDoc.id) {
                        this.expandedFolderId = newDoc.id;
                    }
                }
            },
        },
    },
    methods: {
        ...mapActions("collection", [
            "removeItem",
            "updateItemTranscription",
            "fetchDocumentTranscriptions",
        ]),

        /**
         * set open tab to null if clicking the active tab, otherwise set new active tab
         */
        async toggleFolder(docId) {
            if (this.expandedFolderId === docId) {
                this.expandedFolderId = null;
                return;
            }
            const inStore = this.storeDocuments.find(
                (d) => d.pk === docId,
            )?.transcriptions;
            const inCache = this.documentTranscriptions[docId];
            if (!inStore && !inCache) {
                this.loadingFolderId = docId;
                // fetch transcription layers to cache names for dropdown
                await this.fetchDocumentTranscriptions(docId);
                this.loadingFolderId = null;
            }
            this.expandedFolderId = docId;
        },

        /**
         * remove a part from the collection on state
         */
        removeSelectedPart(partPk) {
            this.removeItem(partPk);
        },

        /**
         * change the transcription on a part on state
         */
        updateTranscription(item, newTranscriptionId) {
            this.updateItemTranscription({
                partPk: item.document_part,
                transcriptionId: parseInt(newTranscriptionId),
            });
        },

        /**
         * get a thumbnail for an image
         */
        getThumbnailUrl(part) {
            const img = part.thumbnail;
            if (!img) return null;
            if (typeof img === "string") return img;
            return img.thumbnails?.card || img.uri || null;
        },

        /**
         * get the selected transcription layer ID as a string; fallback to manual if missing
         */
        getPartLayerId(part, doc) {
            if (part.transcription_layer) return String(part.transcription_layer);

            if (doc.baseTransOpts && doc.baseTransOpts.length > 0) {
                const manual = doc.baseTransOpts.find((opt) => opt.label === "manual");
                return manual ? manual.value : doc.baseTransOpts[0].value;
            }
            return "";
        },
    },
};
</script>
