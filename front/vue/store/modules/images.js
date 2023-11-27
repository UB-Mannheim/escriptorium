import axios from "axios";
import { retrieveDocument, retrieveDocumentParts } from "../../../src/api";
import forms from "../util/initialFormState";

// initial state
const state = () => ({
    loading: {
        document: true,
        groups: true,
        images: true,
        models: true,
    },
    nextPage: "",
    selectedParts: [],
});

const getters = {};

const actions = {
    async fetchDocument({ commit, dispatch, rootState }) {
        commit("setLoading", { key: "document", loading: true });
        const { data } = await retrieveDocument(rootState.document.id);
        if (data) {
            commit("document/setReadDirection", data.read_direction, {
                root: true,
            });
            commit("document/setName", data.name, { root: true });
            commit("document/setPartsCount", data.parts_count, { root: true });
            commit("document/setProjectSlug", data.project, { root: true });
            commit("document/setProjectId", data.project_id, { root: true });
            commit("document/setProjectName", data.project_name, {
                root: true,
            });
            await commit(
                "document/setRegionTypes",
                [
                    ...data.valid_block_types,
                    { pk: "Undefined", name: "(Undefined region type)" },
                    { pk: "Orphan", name: "(Orphan lines)" },
                ],
                { root: true },
            );
            // select all region types on forms that have that key
            Object.keys(forms)
                .filter((form) =>
                    Object.prototype.hasOwnProperty.call(
                        forms[form],
                        "regionTypes",
                    ),
                )
                .forEach((form) => {
                    commit(
                        "forms/setFieldValue",
                        {
                            form,
                            field: "regionTypes",
                            value: rootState.document.regionTypes.map((rt) =>
                                rt.pk.toString(),
                            ),
                        },
                        { root: true },
                    );
                });

            // set groups/users
            commit("document/setSharedWithGroups", data.shared_with_groups, {
                root: true,
            });
            commit("document/setSharedWithUsers", data.shared_with_users, {
                root: true,
            });

            // set default text direction for the segment form
            commit(
                "forms/setFieldValue",
                {
                    form: "segment",
                    field: "textDirection",
                    value:
                        data.read_direction === "rtl"
                            ? "horizontal-rl"
                            : "horizontal-lr",
                },
                { root: true },
            );

            commit("setLoading", { key: "document", loading: false });

            if (data.parts_count > 0) {
                // kickoff parts fetch
                commit("setLoading", { key: "images", loading: true });
                try {
                    await dispatch("fetchParts");
                    commit("setLoading", { key: "images", loading: false });
                } catch (error) {
                    commit("setLoading", { key: "images", loading: false });
                    dispatch("alerts/addError", error, { root: true });
                }
            }
        } else {
            commit("setLoading", { key: "document", loading: false });
            throw new Error("Unable to retrieve document");
        }
    },
    /**
     * Fetch the next page of images, retrieved from fetchImages, and add
     * all of its projects on the state.
     */
    async fetchNextPage({ state, commit, dispatch, rootState }) {
        commit("setLoading", { key: "images", loading: true });
        try {
            console.log(state.nextPage);
            const { data } = await axios.get(state.nextPage);
            if (data?.results) {
                data.results.forEach((part) => {
                    commit(
                        "document/addPart",
                        {
                            ...part,
                            title: `${part.title} - ${part.filename}`,
                            thumbnail: part.image?.thumbnails?.card,
                            href: `/document/${rootState.document.id}/part/${part.pk}/edit/`,
                        },
                        { root: true },
                    );
                });
                commit("setNextPage", data.next || "");
            } else {
                throw new Error("Unable to retrieve additional images");
            }
            commit("setLoading", { key: "images", loading: false });
        } catch (error) {
            commit("setLoading", { key: "images", loading: false });
            dispatch("alerts/addError", error, { root: true });
        }
    },
    /**
     * Fetch the images with thumbnails.
     */
    async fetchParts({ commit, rootState }) {
        const { data } = await retrieveDocumentParts({
            documentId: rootState.document.id,
            field: "order",
            direction: 1,
            pageSize: 50,
        });
        if (data?.results) {
            commit(
                "document/setParts",
                data.results.map((part) => ({
                    ...part,
                    title: `${part.title} - ${part.filename}`,
                    thumbnail: part.image?.thumbnails?.card,
                    href: `/document/${rootState.document.id}/part/${part.pk}/edit/`,
                })),
                { root: true },
            );
            commit("setNextPage", data.next || "");
        } else {
            throw new Error("Unable to retrieve document images");
        }
    },
    setSelectedPartsByOrder({ commit, rootState }, selected) {
        const parts = rootState.document.parts.map((part) => {
            if (selected.includes(part.order + 1)) return part.pk;
        });
        commit("setSelectedParts", parts);
    },
    togglePartSelected({ commit, state }, pk) {
        if (state.selectedParts.includes(pk)) {
            commit("deselectPart", pk);
        } else {
            commit("selectPart", pk);
        }
    },
};

const mutations = {
    deselectPart(state, partPk) {
        const clone = structuredClone(state.selectedParts);
        clone.splice(clone.indexOf(partPk), 1);
        state.selectedParts = clone;
    },
    selectPart(state, partPk) {
        const clone = structuredClone(state.selectedParts);
        clone.push(partPk);
        state.selectedParts = clone;
    },
    setLoading(state, { key, loading }) {
        state.loading[key] = loading;
    },
    setNextPage(state, nextPage) {
        state.nextPage = nextPage;
    },
    setSelectedParts(state, parts) {
        state.selectedParts = parts;
    },
};

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations,
};
