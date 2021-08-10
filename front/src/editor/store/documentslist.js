import { assign } from 'lodash'
import * as api from '../api'

export const initialState = () => ({
    tags: [],
    checkedtags: [],
    maptags: [],
    filters: "",
    documentID: 0,
    projectID: 0,
    field_errors: '',
    checkboxlist: []
})

export const mutations = {
    setDocTags (state, tags) {
        state.tags = tags;
    },
    setCheckedTags (state, tags) {
        state.checkedtags = tags;
    },
    setUnlinkedTags (state, tags) {
        state.maptags = tags;
    },
    setFilters (state, filters) {
        state.filters = filters
    },
    setDocumentID (state, idd) {
        state.documentID = idd
    },
    setProjectID (state, id) {
        state.projectID = id
    },
    setFormError (state, val) {
        state.field_errors = val
    },
    setCheckboxList (state, {selected, bool}) {
        if(bool) state.checkboxlist.push(selected)
        else {
            let index = state.checkboxlist.indexOf(selected);
            if (index > -1) {
                state.checkboxlist.splice(index, 1);
            }
        }
    },
}

export const actions = {
    async getunlinktagbydocument ({state, commit}, idd) {
        const resp = await api.retriveUnlinkTagByDocument(idd);
        commit('setCheckedTags', resp.data.selectedtags);
        commit('setUnlinkedTags', JSON.parse(resp.data.tags));
    },
    async getalltagsproject ({state, commit}) {
        const resp = await api.retriveTagOnProject(state.projectID);
        commit('setCheckedTags', resp.data.selectedtags);
        commit('setUnlinkedTags', JSON.parse(resp.data.tags));
    },
    async updatedocumenttags ({state, commit}, data) {
        let resp = null;
        if(state.documentID != 0) resp = await api.assignTagOnDocument(state.documentID, data);
        else resp = await api.assignTagOnDocumentList(state.projectID, data);
    }
}

export default {
    namespaced: true,
    state: initialState(),
    mutations,
    actions
}
