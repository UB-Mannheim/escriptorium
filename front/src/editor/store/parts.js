import { assign } from "lodash";
import { getMetadataCRUD } from "../../../vue/store/util/metadata";
import {
    retrieveDocumentPart,
    retrieveDocumentPartByOrder,
    updatePart as apiUpdatePart,
    rotateDocumentPart,
    createPartMetadata as apiCreatePartMetadata,
    retrievePartMetadata,
    updatePartMetadata as apiUpdatePartMetadata,
    deletePartMetadata as apiDeletePartMetadata,
} from "../../api";

export const initialState = () => ({
    pk: null,
    loaded: false,
    previous: null,
    next: null,
    order: -1,
    image: {},
    bw_image: {},
    filename: "",
    name: "",
    title: "",
    recoverable: null,
    transcription_progress: null,
    typology: null,
    workflow: {},
    metadata: null,
    typologies: null,
    comments: null,
});

export const mutations = {
    setPartPk(state, pk) {
        state.pk = pk;
    },
    setOrder(state, order) {
        state.order = order;
    },
    load(state, part) {
        assign(state, part);
        state.loaded = true;
    },
    addMetadatum(state, metadatum) {
        const metadata = structuredClone(state.metadata);
        metadata.push(metadatum);
        state.metadata = metadata;
    },
    removeMetadatum(state, removePk) {
        const clone = structuredClone(state.metadata);
        state.metadata = clone.filter(
            (metadatum) => metadatum.pk.toString() !== removePk.toString(),
        );
    },
    updateMetadatum(state, metadatumToUpdate) {
        const metadata = structuredClone(state.metadata).map((m) => {
            if (m.pk.toString() === metadatumToUpdate.pk.toString()) {
                return metadatumToUpdate;
            }
            return m;
        });
        state.metadata = metadata;
    },
    setMetadata(state, metadata) {
        state.metadata = metadata;
    },
    reset(state) {
        assign(state, initialState());
    },
    setLoaded(state, loaded) {
        state.loaded = loaded;
    },
};

export const actions = {
    // fetch a single part from API and set its data on state
    async fetchPart({ commit, dispatch, rootState }, { pk, order }) {
        if (!rootState.transcriptions.all.length) {
            await dispatch("document/fetchDocument", rootState.document.id, {
                root: true,
            });
        }
        var resp;
        if (pk) {
            commit("setPartPk", pk);
            resp = await retrieveDocumentPart(rootState.document.id, pk);
        } else {
            resp = await retrieveDocumentPartByOrder(
                rootState.document.id,
                order,
            );
            commit("setPartPk", resp.data.pk);
        }

        let { data } = resp;

        // set order on state
        if (order) {
            commit("setOrder", order);
        } else if (Object.hasOwn(data, "order")) {
            commit("setOrder", parseInt(data.order));
        }
        delete data.order;

        // map lines and region types to names and set on state, then remove from data object
        data.lines.forEach(function (line) {
            let type_ =
                line.typology &&
                rootState.document.types.lines.find(
                    (t) => t.pk == line.typology,
                );
            line.type = type_ && type_.name;
        });
        commit("lines/set", data.lines, { root: true });
        delete data.lines;

        data.regions.forEach(function (reg) {
            let type_ =
                reg.typology &&
                rootState.document.types.regions.find(
                    (t) => t.pk == reg.typology,
                );
            reg.type = type_ && type_.name;
        });
        commit("regions/set", data.regions, { root: true });
        delete data.regions;

        // set form state for the details modal
        commit(
            "forms/setFormState",
            {
                form: "elementDetails",
                formState: {
                    comments: data.comments,
                    metadata: data.metadata,
                    name: data.name,
                    typology: data.typology,
                },
            },
            { root: true },
        );

        // load the rest of the data object onto state with existing key/value pairs
        commit("load", data);
    },

    // save part changes from the modal form
    async savePartChanges({ commit, rootState, state }) {
        if (rootState?.forms?.elementDetails) {
            // start loading
            commit("setLoaded", false);

            // get element details form data
            const { comments, metadata, name, typology } =
                rootState.forms.elementDetails;

            // make api call(s) to update metadata
            const { metadataToCreate, metadataToUpdate, metadataToDelete } =
                getMetadataCRUD({
                    stateMetadata: state.metadata,
                    formMetadata: metadata,
                });
            const metadataResponses = await Promise.all([
                ...metadataToCreate.map((m) =>
                    apiCreatePartMetadata(rootState.document.id, state.pk, m),
                ),
                ...metadataToUpdate.map((metadatum) =>
                    apiUpdatePartMetadata(
                        rootState.document.id,
                        state.pk,
                        metadatum.pk,
                        metadatum,
                    ),
                ),
                ...metadataToDelete.map((metadatum) =>
                    apiDeletePartMetadata(
                        rootState.document.id,
                        state.pk,
                        metadatum.pk,
                    ),
                ),
            ]);

            // update state for metadata responses
            metadataResponses
                .filter((r) => !!r)
                .forEach(async (response) => {
                    if (response.status === 200) {
                        // updated
                        const { data } = response;
                        commit("updateMetadatum", data);
                    } else if (response.status === 201) {
                        // created
                        const { data } = response;
                        commit("addMetadatum", data);
                    } else if (response.status === 204) {
                        // deleted
                        const { request } = response;
                        const splitURL = request?.responseURL.split("/");
                        const pk = splitURL[splitURL.length - 2];
                        commit("removeMetadatum", pk);
                    }
                });

            // make api call to update part
            const { data } = await apiUpdatePart(
                rootState.document.id,
                state.pk,
                { comments, name, typology },
            );

            // set order on state and remove
            if (Object.hasOwn(data, "order")) {
                commit("setOrder", parseInt(data.order) + 1);
            }
            delete data.order;

            // load remaining data
            commit("load", data);
        }
    },

    async updatePart({ state, commit, rootState }, data) {
        const resp = await apiUpdatePart(rootState.document.id, state.pk, data);
        commit("load", resp.data);
    },

    async rotate({ state, commit, dispatch, rootState }, angle) {
        await rotateDocumentPart(rootState.document.id, state.pk, {
            angle: angle,
        });

        let pk = state.pk;
        commit("regions/reset", {}, { root: true });
        commit("lines/reset", {}, { root: true });
        commit("imageAnnotations/reset", {}, { root: true });
        commit("textAnnotations/reset", {}, { root: true });
        commit("reset");
        await dispatch("fetchPart", { pk: pk });
    },

    async loadPartByOrder({ commit, dispatch, rootState }, order) {
        commit("regions/reset", {}, { root: true });
        commit("lines/reset", {}, { root: true });
        commit("imageAnnotations/reset", {}, { root: true });
        commit("textAnnotations/reset", {}, { root: true });
        commit("reset");
        try {
            await dispatch("fetchPart", { order: order });
            await dispatch(
                "transcriptions/getCurrentContent",
                rootState.transcriptions.selectedTranscription,
                { root: true },
            );
            await dispatch(
                "transcriptions/getComparisonContent",
                {},
                { root: true },
            );
        } catch (err) {
            console.log("couldn't fetch part data!", err);
        }
    },

    async loadPart({ state, commit, dispatch, rootState }, direction) {
        if (!state.loaded || !state[direction]) return;
        let part = state[direction];
        commit("regions/reset", {}, { root: true });
        commit("lines/reset", {}, { root: true });
        commit("imageAnnotations/reset", {}, { root: true });
        commit("textAnnotations/reset", {}, { root: true });
        commit("reset");
        try {
            await dispatch("fetchPart", { pk: part });
            await dispatch(
                "transcriptions/getCurrentContent",
                rootState.transcriptions.selectedTranscription,
                { root: true },
            );
            await dispatch(
                "transcriptions/getComparisonContent",
                {},
                { root: true },
            );
        } catch (err) {
            console.log("couldn't fetch part data!", err);
        }
    },
    async createPartMetadata({ state, commit, rootState }, data) {
        await apiCreatePartMetadata(rootState.document.id, state.pk, data);
        const resp = await retrievePartMetadata(
            rootState.document.id,
            state.pk,
        );
        commit("setMetadata", resp.data.results);
    },
    async updatePartMetadata({ state, rootState }, { pk, data }) {
        await apiUpdatePartMetadata(rootState.document.id, state.pk, pk, data);
    },
    async deletePartMetadata({ state, rootState }, rowPk) {
        await apiDeletePartMetadata(rootState.document.id, state.pk, rowPk);
        var metadata = state.metadata;
        const idx = metadata.findIndex((md) => md.id == rowPk);
        metadata.splice(idx, 1);
    },
};

export default {
    namespaced: true,
    state: initialState(),
    mutations,
    actions,
};
