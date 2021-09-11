import { assign } from 'lodash'
import * as api from '../api'

export const initialState = () => ({
    checkedTags: [],
    mapTags: [],
    documentID: null,
    projectID: null,
    checkboxList: []
})

export const mutations = {
    setCheckedTags (state, tags) {
        state.checkedTags = tags;
    },
    setUnlinkedTags (state, tags) {
        state.mapTags = tags;
    },
    setDocumentID (state, id) {
        state.documentID = id
    },
    setProjectID (state, id) {
        state.projectID = id
    },
    setCheckboxList (state, {selected, bool}) {
        if(bool) state.checkboxList.push(selected)
        else {
            let index = state.checkboxList.indexOf(selected);
            if (index > -1) {
                state.checkboxList.splice(index, 1);
            }
        }
    },
}

export const actions = {
    async getUnlinkTagByDocument ({state, commit}, id) {
        const resp = await api.retrieveUnlinkTagByDocument(id);
        commit('setCheckedTags', resp.data.selectedtags);
        commit('setUnlinkedTags', JSON.parse(resp.data.tags));
    },
    async getAllTagsProject ({state, commit}) {
        const resp = await api.retrieveTagOnProject(state.projectID);
        commit('setUnlinkedTags', JSON.parse(resp.data.tags));
    },
    async updateDocumentTags ({state, commit}, data) {
        if(state.documentID) await api.assignTagOnDocument(state.documentID, data);
        else await api.assignTagOnDocumentList(state.projectID, data);
    }
}

export default {
    namespaced: true,
    state: initialState(),
    mutations,
    actions
}
