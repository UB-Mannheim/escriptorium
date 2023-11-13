import * as api from "../api";
import { retrieveDefaultOntology } from "../../api";

export const initialState = () => ({
    id: null,
    name: "",
    projectSlug: "",
    projectName: "",
    partsCount: 0,
    defaultTextDirection: null,
    mainTextDirection: null,
    readDirection: null,
    types: {},
    blockShortcuts: false,

    annotationTaxonomies: {},

    // Manage panels visibility through booleans
    // Those values are initially populated by localStorage
    visible_panels: {
        source: userProfile.get("visible-panels")
            ? userProfile.get("visible-panels").source
            : false,
        segmentation: userProfile.get("visible-panels")
            ? userProfile.get("visible-panels").segmentation
            : true,
        visualisation: userProfile.get("visible-panels")
            ? userProfile.get("visible-panels").visualisation
            : true,
        diplomatic: userProfile.get("visible-panels")
            ? userProfile.get("visible-panels").diplomatic
            : false,
        metadata: userProfile.get("visible-panels")
            ? userProfile.get("visible-panels").metadata
            : false,
    },

    // "New UI" version of visible_panels management
    // get from userProfile, or by default, [segmentation, visualisation]
    editorPanels: userProfile.get("editor-panels")
        ? userProfile.get("editor-panels")
        : ["segmentation", "visualisation"],

    // Confidence overlay visibility
    confidenceVisible: false,
    // exponential scale factor for confidence overlay
    confidenceScale: 4,

    enabledVKs: userProfile.get("VK-enabled")
        ? userProfile.get("VK-enabled")
        : [],

    defaultTypes: {},
    loading: false,
});

export const mutations = {
    addEditorPanel(state, panel) {
        const editorPanels = structuredClone(state.editorPanels);
        editorPanels.push(panel);
        state.editorPanels = editorPanels;
        // Persist final value in user profile
        userProfile.set("editor-panels", editorPanels);
    },
    setId(state, id) {
        state.id = id;
    },
    setName(state, name) {
        state.name = name;
    },
    setDefaultTextDirection(state, direction) {
        state.defaultTextDirection = direction;
    },
    setMainTextDirection(state, direction) {
        state.mainTextDirection = direction;
    },
    setReadDirection(state, direction) {
        state.readDirection = direction;
    },
    setTypes(state, types) {
        state.types = types;
    },
    setPartsCount(state, count) {
        state.partsCount = count;
    },
    setBlockShortcuts(state, block) {
        state.blockShortcuts = block;
    },
    setVisiblePanels(state, payload) {
        state.visible_panels = Object.assign({}, state.visible_panels, payload);
    },
    setAnnotationTaxonomies(state, { type, taxos }) {
        state.annotationTaxonomies[type] = taxos;
    },
    setEnabledVKs(state, vks) {
        state.enabledVKs = Object.assign([], state.enabledVKs, vks);
    },
    setConfidenceScale(state, scale) {
        state.confidenceScale = scale;
    },
    setConfidenceVizGloballyEnabled(state, enabled) {
        state.confidenceVisible = enabled;
    },
    setProjectSlug(state, projectSlug) {
        state.projectSlug = projectSlug;
    },
    setProjectName(state, projectName) {
        state.projectName = projectName;
    },
    switchEditorPanel(state, { index, panel }) {
        let editorPanels = structuredClone(state.editorPanels);
        if (editorPanels[index] !== panel) {
            // do nothing if it's the same panel
            if (editorPanels.includes(panel)) {
                // if it's open, replace panel at its index with this panel
                const thisPanel = editorPanels[index];
                const thatIndex = editorPanels.indexOf(panel);
                editorPanels[thatIndex] = thisPanel;
            }
            editorPanels[index] = panel;
            state.editorPanels = editorPanels;
            // Persist final value in user profile
            userProfile.set("editor-panels", editorPanels);
        }
    },
    removeEditorPanel(state, panel) {
        let editorPanels = structuredClone(state.editorPanels).filter(
            (editorPanel) => editorPanel.toString() !== panel.toString(),
        );
        state.editorPanels = editorPanels;
        // Persist final value in user profile
        userProfile.set("editor-panels", editorPanels);
    },
    reset(state) {
        Object.assign(state, initialState());
    },
    setDefaultTypes(state, types) {
        state.defaultTypes = types;
    },
    setLoading(state, loading) {
        state.loading = loading;
    },
};

export const actions = {
    async fetchDocument({ state, commit, dispatch }) {
        const resp = await api.retrieveDocument(state.id);
        let data = resp.data;
        var valid_part_types = data.valid_part_types;
        valid_part_types.unshift({ pk: null, name: "Element" });

        // set transcriptions state
        commit("transcriptions/set", data.transcriptions, { root: true });
        // set transcriptions form state
        commit(
            "forms/setFormState",
            {
                form: "transcriptionManagement",
                formState: { transcriptions: data.transcriptions },
            },
            { root: true },
        );

        // set types on state
        const types = {
            regions: data.valid_block_types,
            lines: data.valid_line_types,
            parts: valid_part_types,
        };
        commit("setTypes", types);
        // set types form state
        commit(
            "forms/setFormState",
            {
                form: "ontology",
                formState: { ...types },
            },
            { root: true },
        );
        commit("setProjectSlug", data.project);
        commit("setProjectName", data.project_name);
        commit("setPartsCount", data.parts_count);
        commit("setConfidenceVizGloballyEnabled", data.show_confidence_viz);

        let page = 1;
        var img_taxos = [];
        while (page) {
            let resp = await api.retrieveAnnotationTaxonomies(
                data.pk,
                "image",
                page,
            );
            img_taxos = img_taxos.concat(resp.data.results);
            if (resp.data.next) page++;
            else page = null;
        }
        commit("setAnnotationTaxonomies", { type: "image", taxos: img_taxos });

        page = 1;
        var text_taxos = [];
        while (page) {
            let resp = await api.retrieveAnnotationTaxonomies(
                data.pk,
                "text",
                page,
            );
            text_taxos = text_taxos.concat(resp.data.results);
            if (resp.data.next) page++;
            else page = null;
        }
        commit("setAnnotationTaxonomies", { type: "text", taxos: text_taxos });

        await dispatch("fetchDefaultTypes");
    },

    async togglePanel({ state, commit }, panel) {
        // Toggle the display of a single panel
        let update = {};
        update[panel] = !state.visible_panels[panel];
        commit("setVisiblePanels", update);

        // Persist final value in user profile
        userProfile.set("visible-panels", state.visible_panels);
    },

    async scaleConfidence({ commit }, scale) {
        commit("setConfidenceScale", scale);
    },

    /**
     * Add an editor panel by clicking the "add panel" button (new UI)
     */
    addEditorPanel({ state, commit, dispatch }, panel) {
        if (
            state.editorPanels.length < 3 &&
            !state.editorPanels.includes(panel)
        ) {
            // add to the end
            commit("addEditorPanel", panel);
        } else if (state.editorPanels.length >= 3) {
            dispatch("alerts/addError", "Cannot view more than three panels", {
                root: true,
            });
        }
    },

    /**
     * Fetch default types
     */
    async fetchDefaultTypes({ commit }) {
        let types = {};
        await Promise.all(
            ["regions", "lines", "parts"].map(async (category) => {
                const { data } = await retrieveDefaultOntology(category);
                if (data?.results) {
                    types[category] = data.results;
                }
                let noneType = { pk: null, name: "None" };
                if (category === "parts") noneType.name = "Element";
                types[category] = [noneType, ...types[category]];
                return;
            }),
        );
        commit("setDefaultTypes", types);
    },

    /**
     * Remove an editor panel by clicking the "add panel" button (new UI)
     */
    removeEditorPanel({ state, commit, dispatch }, panel) {
        if (state.editorPanels.length > 0) {
            // remove by name
            commit("removeEditorPanel", panel);
        } else {
            dispatch(
                "alerts/addError",
                "Must have at least one visible panel",
                {
                    root: true,
                },
            );
        }
    },

    saveOntologyChanges({ commit, state }) {
        commit("setLoading", true);
        // TODO: persist changes to ontology.
        // NOTE: colors were saved separately (local settings only), in the modal.
        commit("setLoading", false);
    },

    /**
     * Switch an editor panel out for another one (new UI)
     */
    switchEditorPanel({ commit }, { index, panel }) {
        commit("switchEditorPanel", { index, panel });
    },
};

export default {
    namespaced: true,
    state: initialState(),
    mutations,
    actions,
};
