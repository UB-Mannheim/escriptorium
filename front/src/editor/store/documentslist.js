import { assign } from 'lodash'
import * as api from '../api'

export const initialState = () => ({
    checkedTags: [],
    mapTags: [],
    documentID: null,
    projectID: null,
    checkboxList: [],
    lastChecked: null,
    allProjectTags: [],
    tagColor: null
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
    setLastChecked (state, value) {
        state.lastChecked = value
    },
    setAllProjectTags (state, value) {
        state.allProjectTags = value.map( function(obj) {
            var item = { "pk": obj.id, "name": obj.name, "color": obj.color };
            return item;
        });
    },
    setTagColor (state) {
        let brigth = 0;
        let rColor, bColor, gColor = 0;
        while (brigth < 150) {
            rColor = Math.floor(Math.random() * (255 - 10)) + 10;
            bColor = Math.floor(Math.random() * (255 - 10)) + 10;
            gColor = Math.floor(Math.random() * (255 - 10)) + 10;
            brigth = rColor + bColor + gColor;
        }
        let colorf = "#" + rColor.toString(16) + bColor.toString(16) + gColor.toString(16);
        state.tagColor = colorf
    },
}

export const actions = {
    async getUnlinkTagByDocument ({state, commit}, id) {
        const _document = await api.retrieveDocument(id);
        commit('setCheckedTags', _document.data.tags);
        commit('setUnlinkedTags', state.allProjectTags);
    },
    async getAllTagsProject ({state, commit}) {
        commit('setUnlinkedTags', state.allProjectTags);
    },
    async updateDocumentTags ({state, commit}, data) {
        var selectedId = (data.selectedtags) ? data.selectedtags.split(',') : [];
        var name = data.name;
        if(name) {
            var listProjectTagsId = state.allProjectTags;
            let tagsNames = listProjectTagsId.map((obj) => obj.name);
            if(!tagsNames.includes(name)){
                const tag = await api.createProjectTag(state.projectID, {"name": name, "color": data.color});
                listProjectTagsId.push(tag.data);
                commit('setUnlinkedTags', listProjectTagsId);
                selectedId.push(tag.data.pk.toString());
            }
            else{
                let _name = listProjectTagsId.filter(obj => obj.name == name);
                selectedId.push(_name[0].pk.toString());
            }
        }
        if(state.documentID) {
            await api.updateDocument(state.documentID, {"tags": selectedId});
        }
        else {
            if(state.checkboxList.length > 0){
                for (let i = 0; i < state.checkboxList.length; i++) {
                    const _document = await api.retrieveDocument(state.checkboxList[i]);
                    let _tagsId = _document.data.tags;
                    let tags = _tagsId.concat(selectedId.filter(item => !_tagsId.includes(item)));
                    await api.updateDocument(state.checkboxList[i], {"tags": tags});
                }
            }
        }
    },
    async updateProjectTag ({state, commit}, data) {
        await api.updatetag(state.projectID, data.pk, data);
    },
    async deleteProjectTag ({state, commit}, data) {
        await api.deletetag(state.projectID, data.pk);
    },
    async assignSingleTagToDocuments ({state, commit}, data) {
        if(state.checkboxList.length > 0){
            for (let i = 0; i < state.checkboxList.length; i++) {
                const _document = await api.retrieveDocument(state.checkboxList[i]);
                let _tagsId = _document.data.tags;
                if(data.selected && !_tagsId.includes(data.pk)) _tagsId.push(data.pk);
                else{
                    let index = _tagsId.indexOf(data.pk);
                    if (index > -1) _tagsId.splice(index, 1);
                }
                await api.updateDocument(state.checkboxList[i], {"tags": _tagsId});
            }
        }
    }
}

export default {
    namespaced: true,
    state: initialState(),
    mutations,
    actions
}
