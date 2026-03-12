import axios from "axios";

// initial state
const state = () => ({
    dirty: false,
    loading: false,
    saving: false,
    collections: [],
    currentCollection: {
        id: null,
        name: "",
        /**
         * items: [{
         *     id: Number | null,
         *     document_part: Number,
         *     part_name: String,
         *     document_id: Number,
         *     document_name: String,
         *     transcription_layer: Number,
         * }]
         */
        items: [],
        // defaultTranscriptions stores default transcription per doc pk
        defaultTranscriptions: {},
    },
    // documentTranscriptions stores ALL transcriptions per doc pk
    documentTranscriptions: {},
    tasks: [],
});

const actions = {
    /**
     * add all parts from a document to the virtual collection
     */
    async addAllParts({ commit, dispatch }, { document, transcriptionId }) {
        commit("setLoading", true);
        try {
            const { data: allIds } = await axios.get(`/documents/${document.pk}/part_ids/`);
            let partsMetadata = document.parts || [];

            if (partsMetadata.length < allIds.length) {
                // fetch minimal fields for the grid
                let url = `/documents/${document.pk}/parts/?fields=id,name,image,order`;
                partsMetadata = [];
                // loop through paginated results until 'next' is null
                while (url) {
                    const { data } = await axios.get(url);
                    partsMetadata.push(...(data.results || []));
                    url = data.next;
                }
            }
            await dispatch("addSelectedParts", {
                document,
                partPks: allIds,
                partsOverride: partsMetadata,
                transcriptionId,
            });
        } finally {
            commit("setLoading", false);
        }
    },
    /**
     * add selected parts to the virtual collection
     */
    async addSelectedParts({ commit, state }, { document, partPks, partsOverride = null }) {
        const documentId = document.pk || document.id;
        // attempt to use document's default transcription
        let transcriptionId = state.currentCollection.defaultTranscriptions[documentId];
        if (!transcriptionId) {
            const manual = document.transcriptions?.find((t) => t.name === "manual")
                || document.transcriptions?.[0];
            transcriptionId = manual ? (manual.id || manual.pk) : null;
            if (document) {
                commit("setDefaultTranscription", { documentId, transcriptionId });
            }
        }
        const sourceParts = partsOverride || document.parts || [];
        const selectedParts = sourceParts.filter((p) => partPks.includes(p.pk || p.id));
        commit("addItems", {
            document,
            parts: selectedParts,
            transcriptionId,
        });
    },
    /**
     * fetch all collections owned by the current user
     */
    async fetchCollections({ commit }) {
        try {
            let url = "/collections/";
            const collections = [];
            while (url) {
                const { data } = await axios.get(url);
                collections.push(...(data.results || []));
                url = data.next;
            }
            commit("setCollections", collections);
        } catch (error) {
            console.error("Failed to fetch collections:", error);
        }
    },

    /**
     * load a collection into state
     */
    async loadCollection({ commit, dispatch }, collectionId) {
        if (!collectionId) {
            commit("setCurrentCollection", {
                id: null,
                name: "",
                items: [],
                default_transcriptions: {},
            });
            return;
        }
        commit("setLoading", true);
        try {
            // GET the detail endpoint to get basic metadata
            const { data: collection } = await axios.get(`/collections/${collectionId}/`);
            commit("setCurrentCollection", { ...collection, items: [] });
            let url = `/collections/${collectionId}/items/?page_size=200`;
            while (url) {
                // loop through paginated item lists
                const { data } = await axios.get(url);
                commit("pushCollectionItems", data.results);
                url = data.next;
            }
        } catch (error) {
            dispatch("alerts/addError", error, { root: true });
            // fallback to clear state if the fetch fails
            commit("setCurrentCollection", {
                id: null,
                name: "",
                items: [],
                default_transcriptions: {},
            });
        } finally {
            commit("setLoading", false);
        }
    },
    /**
     * create or update the virtual collection in the DB
     */
    async saveCollection({ state, commit, dispatch }) {
        commit("setSaving", true);
        const payload = {
            name: state.currentCollection.name,
            items_to_save: state.currentCollection.items.map((item) => ({
                document_part: item.document_part,
                transcription_layer: item.transcription_layer,
            })),
            default_transcriptions: state.currentCollection.defaultTranscriptions,
        };

        const url = state.currentCollection.id
            ? `/collections/${state.currentCollection.id}/`
            : "/collections/";

        const method = state.currentCollection.id ? "put" : "post";
        const { data } = await axios[method](url, payload);

        commit("setCurrentCollection", data);
        commit("setSaving", false);
        dispatch("fetchCollections");
    },
    /**
     * remove a single part from the virtual collection (local state only)
     */
    removeItem({ commit }, partId) {
        commit("removeItem", partId);
    },
    /**
     * update the default transcription layer for a document
     */
    setDefaultTranscription({ commit }, { documentId, transcriptionId }) {
        commit("setDefaultTranscription", { documentId, transcriptionId });
    },
    /**
     * update the transcription layer selected for a single item
     */
    updateItemTranscription({ commit }, { partPk, transcriptionId }) {
        commit("setItemTranscriptionLayer", { partId: partPk, transcriptionId });
    },
    /**
     * fetch document transcriptions if they aren't already cached
     */
    async fetchDocumentTranscriptions({ commit, dispatch, state }, documentId) {
        if (state.documentTranscriptions[documentId]) return;

        try {
            const { data } = await axios.get(`/documents/${documentId}/`);
            commit("setDocumentTranscriptions", {
                documentId,
                transcriptions: data.transcriptions || [],
            });
        } catch (error) {
            dispatch("alerts/addError", error, { root: true });
            // cache empty array to prevent infinite retries on failure
            commit("setDocumentTranscriptions", { documentId, transcriptions: [] });
        }
    },
    /**
     * fetch task groups associated with a collection
     */
    async fetchCollectionTasks({ commit, state }) {
        const { data } = await axios.get(`/taskgroup/?collection=${state.currentCollection.id}`);
        commit("setTasks", data.results);
    },
    /**
     * submit collection to the backend for model training
     */
    async trainModel({ dispatch, state }, { modelType, payload }) {
        const collectionId = state.currentCollection.id;
        if (!collectionId) {
            dispatch(
                "alerts/addError",
                "The selection must be saved as a collection before training.",
                { root: true }
            );
        }
        if (modelType === "recognizer") {
            return await axios.post(`/collections/${collectionId}/train_recognizer/`, payload);
        } else if (modelType === "segmenter") {
            return await axios.post(`/collections/${collectionId}/train_segmenter/`, payload);
        }
    },
};

const mutations = {
    /**
     * add items to the collection state
     */
    addItems(state, { document, parts, transcriptionId }) {
        parts.forEach((part) => {
            // check if already exists to prevent duplicates
            const partId = part.pk || part.id;
            const exists = state.currentCollection.items.some(
                (item) => item.document_part === partId
            );

            if (!exists) {
                state.currentCollection.items.push({
                    id: null, // new collection, no id
                    document_part: partId,
                    part_name: part.name || `Part ${part.order + 1}`,
                    thumbnail: part.image,
                    document_id: document.pk || document.id,
                    document_name: document.name,
                    transcription_layer: transcriptionId,
                    part_order: part.order,
                });
                state.dirty = true;
            }
        });
    },
    /**
     * remove an item from the collection state
     */
    removeItem(state, partId) {
        state.currentCollection.items = state.currentCollection.items.filter(
            (i) => i.document_part !== partId
        );
        state.dirty = true;
    },
    /**
     * set the collection on state
     */
    setCurrentCollection(state, collection) {
        state.currentCollection = {
            ...collection,
            items: collection.items || state.currentCollection?.items || [],
            defaultTranscriptions: collection.default_transcriptions || {},
        };
        state.dirty = false;
    },
    /**
     * set the collection name on state
     */
    setCollectionName(state, name) {
        state.currentCollection.name = name;
        state.dirty = true;
    },
    /**
     * set the default transcription on state
     */
    setDefaultTranscription(state, { documentId, transcriptionId }) {
        state.currentCollection.defaultTranscriptions = {
            ...state.currentCollection.defaultTranscriptions,
            [documentId]: transcriptionId
        };
        state.dirty = true;
    },
    /**
     * set the loading state
     */
    setLoading(state, loading) {
        state.loading = loading;
    },
    /**
     * set the saving state
     */
    setSaving(state, saving) {
        state.saving = saving;
    },
    /**
     * set the transcription layer ID for an individual item on state
     */
    setItemTranscriptionLayer(state, { partId, transcriptionId }) {
        const item = state.currentCollection.items.find((i) => i.document_part === partId);
        if (item) {
            item.transcription_layer = transcriptionId;
            state.dirty = true;
        }
    },
    /**
     * set the collections list on state
     */
    setCollections(state, collections) {
        state.collections = collections;
    },
    /**
     * set the transcriptions for a specific document into the cache
     */
    setDocumentTranscriptions(state, { documentId, transcriptions }) {
        state.documentTranscriptions = {
            ...state.documentTranscriptions,
            [documentId]: transcriptions
        };
    },
    /**
     * push raw collection items from the API into state
     */
    pushCollectionItems(state, items) {
        // check if already exists to prevent duplicates
        const existingIds = new Set(
            state.currentCollection.items.map((i) => i.document_part)
        );
        items.forEach((item) => {
            if (!existingIds.has(item.document_part)) {
                state.currentCollection.items.push({
                    id: item.id,
                    document_part: item.document_part,
                    part_name: item.part_name,
                    thumbnail: item.thumbnail,
                    document_id: item.document_id,
                    document_name: item.document_name,
                    transcription_layer: item.transcription_layer,
                    part_order: item.part_order,
                });
                existingIds.add(item.document_part);
            }
        });
    },
    /**
     * set the tasks list on state
     */
    setTasks(state, tasks) {
        state.tasks = tasks;
    },
};

export default {
    namespaced: true,
    state,
    mutations,
    actions,
};
