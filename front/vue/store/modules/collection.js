import axios from "axios";

// initial state
const state = () => ({
    loading: false,
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
                const ids = allIds.join(",");
                let url = `/documents/${document.pk}/parts/?ids=${ids}&fields=id,name,image,order`;
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
                commit("setDocumentDefault", { documentId, transcriptionId });
            }
        }
        const sourceParts = partsOverride || document.parts;
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
            const { data } = await axios.get("/collections/");
            commit("setCollections", data.results);
        } catch (error) {
            console.error("Failed to fetch collections:", error);
        }
    },

    /**
     * load a collection into state
     */
    loadCollection({ commit, state }, collectionId) {
        if (!collectionId) {
            commit("setCurrentCollection", {
                id: null,
                name: "",
                items: [],
                default_transcriptions: {},
            });
            return;
        }
        const collection = state.collections.find((c) => c.id === parseInt(collectionId));
        if (collection) {
            commit("setCurrentCollection", collection);
        }
    },
    /**
     * create or update the virtual collection in the DB
     */
    async saveCollection({ state, commit, dispatch }) {
        commit("setLoading", true);
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
        commit("setLoading", false);
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
                    part_image: part.image,
                    document_id: document.pk || document.id,
                    document_name: document.name,
                    transcription_layer: transcriptionId,
                });
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
    },
    /**
     * set the collection on state
     */
    setCurrentCollection(state, collection) {
        state.currentCollection = {
            ...collection,
            defaultTranscriptions: collection.default_transcriptions || {},
        };
    },
    /**
     * set the collection name on state
     */
    setCollectionName(state, name) {
        state.currentCollection.name = name;
    },
    /**
     * set the default transcription on state
     */
    setDefaultTranscription(state, { documentId, transcriptionId }) {
        state.currentCollection.defaultTranscriptions = {
            ...state.currentCollection.defaultTranscriptions,
            [documentId]: transcriptionId
        };
    },
    /**
     * set the loading state
     */
    setLoading(state, loading) {
        state.loading = loading;
    },
    /**
     * set the transcription layer ID for an individual item on state
     */
    setItemTranscriptionLayer(state, { partId, transcriptionId }) {
        const item = state.currentCollection.items.find((i) => i.document_part === partId);
        if (item) {
            item.transcription_layer = transcriptionId;
        }
    },
    /**
     * set the collections list on state
     */
    setCollections(state, collections) {
        state.collections = collections;
    },
};

export default {
    namespaced: true,
    state,
    mutations,
    actions,
};