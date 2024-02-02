import { assign } from "lodash";
import * as api from "../api";
import { updateTranscription } from "../../api/document";

export const initialState = () => ({
    all: [],
    selectedTranscription: null,
    comparedTranscriptions: [],
    transcriptionsLoaded: false,
    transcriptionToDelete: null,
    saveLoading: false,
});

export const mutations = {
    addComparedTranscription(state, pk) {
        const clone = structuredClone(state.comparedTranscriptions);
        clone.push(pk);
        state.comparedTranscriptions = clone;
    },
    setComparedTranscriptions(state, transcriptions) {
        state.comparedTranscriptions = transcriptions;
    },
    set(state, transcriptions) {
        // use structuredClone for proper reactivity in other components
        state.all = structuredClone(transcriptions);
    },
    remove(state, pk) {
        let index = state.all.findIndex((t) => t.pk == pk);
        if (index < 0) return;
        Vue.delete(state.all, index);
    },
    setSelectedTranscription(state, pk) {
        state.selectedTranscription = pk;
    },
    removeComparedTranscription(state, pk) {
        let index = state.comparedTranscriptions.findIndex((tr) => tr === pk);
        if (index < 0) return;
        Vue.delete(state.comparedTranscriptions, index);
    },
    hasLoadedTranscriptions(state, value) {
        state.transcriptionsLoaded = value;
    },
    reset(state) {
        assign(state, initialState());
    },
    setTranscriptionToDelete(state, transcription) {
        state.transcriptionToDelete = transcription;
    },
    setSaveLoading(state, loading) {
        state.saveLoading = loading;
    },
};

export const actions = {
    async bulkCreate({ commit, rootState }, transcriptions) {
        let data = transcriptions.map((l) => {
            return {
                line: l.line,
                transcription: l.transcription,
                content: l.content,
            };
        });

        try {
            const resp = await api.bulkCreateLineTranscriptions(
                rootState.document.id,
                rootState.parts.pk,
                { lines: data },
            );
            let createdTrans = resp.data;
            commit("lines/createTranscriptions", createdTrans, { root: true });
        } catch (err) {
            console.log("couldn't create transcription lines", err);
        }
    },

    async bulkUpdate({ rootState }, transcriptions) {
        let data = transcriptions.map((l) => {
            return {
                pk: l.pk,
                content: l.content,
                line: l.line,
                transcription: l.transcription,
            };
        });

        try {
            await api.bulkUpdateLineTranscriptions(
                rootState.document.id,
                rootState.parts.pk,
                { lines: data },
            );
            // No store update ????
        } catch (err) {
            console.log("couldn't update transcription lines", err);
        }
    },

    async fetchContent({ commit, rootState }, transcription) {
        // first create a default transcription for every line
        rootState.lines.all.forEach(function (line) {
            const tr = {
                line: line.pk,
                transcription: transcription,
                content: "",
                version_author: null,
                version_source: null,
                version_updated_at: null,
            };
            commit(
                "lines/setTranscriptions",
                { pk: line.pk, transcription: tr },
                { root: true },
            );
        });

        //  then fetch all content page by page
        let fetchPage = async function (page) {
            const resp = await api.retrievePage(
                rootState.document.id,
                rootState.parts.pk,
                transcription,
                page,
            );

            let data = resp.data;
            for (var i = 0; i < data.results.length; i++) {
                let line = rootState.lines.all.find(
                    (l) => l.pk == data.results[i].line,
                );
                commit(
                    "lines/setTranscriptions",
                    { pk: line.pk, transcription: data.results[i] },
                    { root: true },
                );
            }
            if (data.next) await fetchPage(page + 1);
        };
        await fetchPage(1);
        commit("hasLoadedTranscriptions", true);
    },

    async updateLineTranscriptionVersion(
        { commit, dispatch, rootState },
        { line, content },
    ) {
        commit(
            "lines/updateTranscriptionVersion",
            { pk: line.pk, content: content },
            { root: true },
        );

        const l = rootState.lines.all.find((li) => li.pk == line.pk);
        let data = {
            content: l.currentTrans.content,
            line: l.currentTrans.line,
            transcription: l.currentTrans.transcription,
            avg_confidence: null,
            graphs: null,
        };
        if (rootState.lines.editedLine) {
            commit("lines/setEditedLine", l, { root: true });
        }

        if (l.currentTrans.pk) {
            await dispatch("updateContent", {
                pk: l.currentTrans.pk,
                content: data,
                currentTransLine: l.currentTrans.line,
            });
        } else {
            await dispatch("createContent", {
                content: data,
                currentTransLine: l.currentTrans.line,
            });
        }
    },

    async createContent({ commit, rootState }, { content, currentTransLine }) {
        try {
            const resp = await api.createContent(
                rootState.document.id,
                rootState.parts.pk,
                content,
            );
            commit(
                "lines/setTranscriptions",
                { pk: currentTransLine, transcription: resp.data },
                { root: true },
            );
            commit("lines/updateCurrentTrans", resp.data.transcription, {
                root: true,
            });
        } catch (err) {
            console.log("couldn't create transcription!", err);
        }
    },

    async updateContent(
        { commit, rootState },
        { pk, content, currentTransLine },
    ) {
        try {
            const resp = await api.updateContent(
                rootState.document.id,
                rootState.parts.pk,
                pk,
                content,
            );
            commit(
                "lines/setTranscriptions",
                { pk: currentTransLine, transcription: resp.data },
                { root: true },
            );
            commit("lines/updateCurrentTrans", resp.data.transcription, {
                root: true,
            });
        } catch (err) {
            console.log("couldn't update transcription!", err);
        }
    },

    async archive({ commit, rootState }, transPk) {
        await api
            .archiveTranscription(rootState.document.id, transPk)
            .then((resp) => {
                commit("remove", transPk);
            });
    },

    getComparisonContent({ state, dispatch }) {
        state.comparedTranscriptions.forEach(async function (tr, i) {
            if (tr != state.selectedTranscription) {
                await dispatch("fetchContent", tr);
            }
        });
    },

    async getCurrentContent({ state, commit, dispatch }, transcription) {
        commit("hasLoadedTranscriptions", false);
        await dispatch("fetchContent", transcription);
        commit("lines/updateCurrentTrans", state.selectedTranscription, {
            root: true,
        });
    },

    /**
     * Open the "delete transcription" modal.
     */
    openDeleteModal({ commit }, transcription) {
        commit("setTranscriptionToDelete", transcription);
        commit(
            "globalTools/setModalOpen",
            { key: "deleteTranscription", open: true },
            { root: true },
        );
    },
    /**
     * Close the "delete transcription" modal.
     */
    closeDeleteModal({ commit }) {
        commit("setTranscriptionToDelete", null);
        commit(
            "globalTools/setModalOpen",
            { key: "deleteTranscription", open: false },
            { root: true },
        );
    },
    /**
     * Delete a single transcription
     */
    async deleteTranscription({ commit, dispatch, rootState, state }) {
        // archive transcription
        await dispatch("archive", state.transcriptionToDelete.pk);
        // update form state
        let formClone = structuredClone(
            rootState.forms.transcriptionManagement.transcriptions,
        ).filter((item) => item.pk !== state.transcriptionToDelete.pk);
        commit(
            "forms/setFieldValue",
            {
                form: "transcriptionManagement",
                field: "transcriptions",
                value: formClone,
            },
            { root: true },
        );
        // close modal
        dispatch("closeDeleteModal");
    },
    /**
     * Save all transcriptions on the document and set results on state
     */
    async saveTranscriptionsChanges({ commit, rootState }) {
        commit("setSaveLoading", true);
        try {
            const updatedTranscriptions = await Promise.all(
                rootState.forms.transcriptionManagement.transcriptions.map(
                    async (formTranscription) =>
                        await updateTranscription({
                            documentId: rootState.document.id,
                            transcriptionId: formTranscription.pk,
                            // only name and comments are editable, at least for now
                            name: formTranscription.name,
                            comments: formTranscription.comments,
                        }),
                ),
            );
            commit(
                "set",
                updatedTranscriptions.map((t) => t.data),
            );
        } catch (err) {
            console.log("couldn't edit transcriptions", err);
            commit("setSaveLoading", false);
        }
        commit("setSaveLoading", false);
    },
};

export default {
    namespaced: true,
    state: initialState(),
    mutations,
    actions,
};
