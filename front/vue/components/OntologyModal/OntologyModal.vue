<template>
    <EscrModal class="escr-edit-ontology">
        <template #modal-header>
            <h2>Ontology</h2>
            <EscrButton
                color="text"
                :disabled="disabled"
                :on-click="onCancel"
                size="small"
            >
                <template #button-icon>
                    <XIcon />
                </template>
            </EscrButton>
        </template>
        <template #modal-content="{ scroll }">
            <SegmentedButtonGroup
                name="ontology-type"
                color="secondary"
                :disabled="disabled"
                :options="tabOptions"
                :on-change-selection="onTabChange"
            />
            <h3 v-if="!['image', 'text'].includes(tab)">
                Default {{ tabLabel }} Types
            </h3>
            <table
                v-if="defaultTypesWithColor && defaultTypesWithColor[tab]"
                class="escr-table"
            >
                <thead>
                    <tr>
                        <th class="checkbox-column" />
                        <th class="name-column">
                            <div><span>Name</span></div>
                        </th>
                        <th
                            v-if="['lines', 'regions'].includes(tab)"
                            class="color-column"
                        >
                            <div><span>Color</span></div>
                        </th>
                    </tr>
                </thead>
                <tbody>
                    <tr
                        v-for="item in defaultTypesWithColor[tab]"
                        :key="item.pk"
                    >
                        <td class="checkbox-column">
                            <input
                                type="checkbox"
                                :disabled="disabled || item.pk === null"
                                :checked="isSelected(item) || item.pk === null"
                                @change="(e) => onCheckItem(item, e.target.checked)"
                            >
                        </td>
                        <td class="name-column">
                            <span>{{ item.name }}</span>
                        </td>
                        <td
                            v-if="['lines', 'regions'].includes(tab)"
                            class="color-column"
                        >
                            <input
                                type="color"
                                class="escr-color-button"
                                aria-label="select color"
                                :value="item.color"
                                :disabled="disabled"
                                @change="(e) => setTypeColor(e, item)"
                            >
                        </td>
                    </tr>
                </tbody>
            </table>
            <h3 :class="{'anno-header': ['image', 'text'].includes(tab) }">
                <span v-if="!['image', 'text'].includes(tab)">Custom {{ tabLabel }} Types</span>
                <span v-else>{{ tabLabel }}</span>
                <EscrButton
                    :disabled="disabled"
                    :on-click="async () => { await onAddType(); scroll(); }"
                    label="Add New"
                    size="small"
                >
                    <template #button-icon>
                        <PlusIcon />
                    </template>
                </EscrButton>
            </h3>
            <AnnotationOntologyTable
                v-if="['image', 'text'].includes(tab)"
                :disabled="disabled"
                :on-remove-type="onRemoveType"
                :types="formState[tab]"
                :tab="tab"
            />
            <table
                v-else-if="customTypes && customTypes[tab]"
                class="escr-table"
            >
                <thead>
                    <tr>
                        <th class="name-column">
                            <div><span>Name</span></div>
                        </th>
                        <th
                            v-if="['lines', 'regions'].includes(tab)"
                            class="color-column"
                        >
                            <div><span>Color</span></div>
                        </th>
                        <th class="remove-column" />
                    </tr>
                </thead>
                <tbody>
                    <tr
                        v-for="item in customTypes[tab]"
                        :key="item.pk"
                    >
                        <td class="name-column escr-text-field">
                            <input
                                type="text"
                                :disabled="disabled"
                                :value="item.name"
                                :invalid="!item.name"
                                @input="(e) => onChangeName(e, item)"
                            >
                        </td>
                        <td
                            v-if="['lines', 'regions'].includes(tab)"
                            class="color-column"
                        >
                            <input
                                type="color"
                                class="escr-color-button"
                                aria-label="select color"
                                :disabled="disabled"
                                :value="item.color"
                                @focusout="(e) => setTypeColor(e, item)"
                            >
                        </td>
                        <td class="remove-column">
                            <EscrButton
                                size="small"
                                color="text"
                                :disabled="disabled"
                                :on-click="() => onRemoveType(item)"
                            >
                                <template #button-icon>
                                    <XIcon />
                                </template>
                            </EscrButton>
                        </td>
                    </tr>
                </tbody>
            </table>
        </template>
        <template #modal-actions>
            <!-- only show save/cancel if changes have been made, otherwise it's confusing -->
            <EscrButton
                color="outline-primary"
                label="Cancel"
                :on-click="onCancel"
                :disabled="disabled"
            />
            <EscrButton
                color="primary"
                label="Save"
                :on-click="onClickSave"
                :disabled="disabled || invalid"
            />
        </template>
    </EscrModal>
</template>
<script>
import { mapActions, mapState } from "vuex";
import AnnotationOntologyTable from "./AnnotationOntologyTable.vue";
import EscrButton from "../Button/Button.vue";
import EscrModal from "../Modal/Modal.vue";
import PlusIcon from "../Icons/PlusIcon/PlusIcon.vue";
import SegmentedButtonGroup from "../SegmentedButtonGroup/SegmentedButtonGroup.vue";
import XIcon from "../Icons/XIcon/XIcon.vue";
import "./OntologyModal.css";
import "../Table/Table.css";
import "../Tags/TagGroup.css";
import { changeHue } from "../../store/util/color";

export default {
    name: "EscrOntologyModal",
    components: {
        AnnotationOntologyTable,
        EscrButton,
        EscrModal,
        PlusIcon,
        SegmentedButtonGroup,
        XIcon,
    },
    props: {
        /**
         * If true, all buttons and form fields are disabled
         */
        disabled: {
            type: Boolean,
            required: true,
        },
        /**
         * Callback for canceling changes (by closing modal or clicking the cancel button)
         */
        onCancel: {
            type: Function,
            required: true,
        },
        /**
         * Callback for clicking the save button
         */
        onSave: {
            type: Function,
            required: true,
        },
    },
    data() {
        return {
            // form state for keeping track of changed colors
            colorFormState: { ["color-directions"]: {}, ["color-regions"]: {} },
            // default colors for types (from baseline editor)
            defaultColors: { lines: "#9A56FF", regions: "#11FF76" },
            // index counter for newly added types
            newTypeIndex: { lines: 1, regions: 1, parts: 1, text: 1, image: 1 },
            // local storage settings names (from baseline editor)
            settingKeys: { lines: "color-directions", regions: "color-regions" },
            // should be one of regions, lines, parts, text, image
            tab: "regions",
        }
    },
    computed: {
        ...mapState({
            formState: (state) => state.forms.ontology,
            documentId: (state) => state.document.id,
            defaultTypes: (state) => state.document.defaultTypes,
            validTypes: (state) => state.document.types,
        }),
        /**
         * Helper method to get color settings from user profile
         */
        colorSettings() {
            // eslint-disable-next-line no-undef
            return userProfile.get(`baseline-editor-${this.documentId}`) || {};
        },
        /**
         * Separate custom types: valid types that are not present in default types
         */
        customTypes() {
            const types = {};
            Object.keys(this.defaultTypes).forEach((key) => {
                types[key] = this.formState[key]
                    .filter(
                        // Exclude all that are in default types
                        (t) => !this.defaultTypes[key].find((dt) => dt.pk === t.pk)
                    )
                    // Exclude pk null in custom types since that's always enabled
                    // and doesn't exist in DB.
                    .filter((t) => t.pk !== null)
                    // Get colors from user settings
                    .map((t, idx) => ({
                        ...t,
                        color: this.getTypeColor(t, idx, key),
                    }));
            });
            return types;
        },
        /**
         * Append color to each default type object. Also add "None".
         */
        defaultTypesWithColor() {
            const defaultsWithColor = {};
            Object.keys(this.defaultTypes).forEach((key) => {
                defaultsWithColor[key] = this.defaultTypes[key].map((t, idx) => ({
                    ...t,
                    color: this.getTypeColor(t, idx, key),
                }));
            });
            return defaultsWithColor;
        },
        /**
         * Consider the form invalid if any of the custom types are missing names.
         */
        invalid() {
            let invalid = false;
            if (this.formState) {
                Object.values(this.formState).forEach((types) => {
                    if (types.some((type) => !type.name)) invalid = true;
                })
            }
            return invalid;
        },
        /**
         * Tab options for which ontology is being edited
         */
        tabOptions() {
            return [
                {
                    label: "Region Types",
                    value: "regions",
                    selected: this.tab === "regions",
                },
                {
                    label: "Line Types",
                    value: "lines",
                    selected: this.tab === "lines",
                },
                {
                    label: "Part Types",
                    value: "parts",
                    selected: this.tab === "parts",
                },
                {
                    label: "Text Annotations",
                    value: "text",
                    selected: this.tab === "text",
                },
                {
                    label: "Image Annotations",
                    value: "image",
                    selected: this.tab === "image",
                },
            ];
        },
        /**
         * Text labels for each tab
         */
        tabLabel() {
            switch (this.tab) {
                case "regions":
                    return "Region";
                case "lines":
                    return "Line";
                case "parts":
                    return "Part";
                case "text":
                    return "Text Annotations";
                case "image":
                    return "Image Annotations";
                default:
                    return "";
            }
        },
    },
    /**
     * On mount, set the existing color settings on state.
     */
    mounted() {
        Object.values(this.settingKeys).forEach((settingKey) => {
            this.colorFormState[settingKey] = this.colorSettings[settingKey] || {};
        });
    },
    methods: {
        ...mapActions("forms", ["handleGenericArrayInput"]),
        async onAddType() {
            // annotation tabs have additional defaults
            let extraValues = {};
            if (["image", "text"].includes(this.tab)) {
                extraValues = {
                    abbreviation: "",
                    components: [],
                    typology: { name: "" },
                    marker_detail: "#28a696",
                    marker_type: this.tab === "text" ? "Background Color" : "Rectangle",
                    has_comments: false,
                }
            }
            // update the form with the current index
            await this.handleGenericArrayInput({
                form: "ontology",
                field: this.tab,
                action: "add",
                value: {
                    name: "",
                    index: `newMeta${this.newTypeIndex[this.tab]}`,
                    ...extraValues,
                },
            });
            // increment index of added types so that we can properly track them individually
            this.newTypeIndex[this.tab] += 1;
        },
        /**
         * Update name and color on form state
         */
        onChangeName(e, item) {
            const value = { ...item, name: e.target.value };
            this.handleGenericArrayInput({
                form: "ontology", field: this.tab, action: "update", value
            });
            const settingKey = this.settingKeys[this.tab];
            // store color by new name on form state
            this.colorFormState[settingKey][value.name] = item.color;
        },
        /**
         * Handle checking and unchecking default types
         */
        onCheckItem(value, checked) {
            if (checked === true) {
                // checking a default item = adding it to the form array
                this.handleGenericArrayInput({
                    form: "ontology", field: this.tab, action: "add", value
                });
            } else {
                // unchecking a default item = removing it from the form array
                this.handleGenericArrayInput({
                    form: "ontology", field: this.tab, action: "remove", value
                });
            }
        },
        /**
         * Handle clicking the save button
         */
        onClickSave() {
            // set colors from form on local storage and active segmenter
            let settings = structuredClone(this.colorSettings);
            Object.values(this.settingKeys).forEach((settingKey) => {
                settings[settingKey] = this.colorFormState[settingKey];
                const event = new CustomEvent(
                    "baseline-editor:ontology-colors",
                    {
                        detail: {
                            category: settingKey,
                            colors: this.colorFormState[settingKey],
                        }
                    },
                );
                document.dispatchEvent(event);
            });
            // eslint-disable-next-line no-undef
            userProfile.set(`baseline-editor-${this.documentId}`, settings);

            // perform onSave callback
            this.onSave();
        },
        /**
         * Handle removing a type from one of the custom lists
         */
        onRemoveType(value) {
            this.handleGenericArrayInput({
                form: "ontology", field: this.tab, value, action: "remove"
            });
        },
        /**
         * Change active tab
         */
        onTabChange(tab) {
            this.tab = tab;
        },
        /**
         * Get color from either form state or defaults
         */
        getTypeColor(type, idx, key) {
            let color = null;
            const settingKey = this.settingKeys[key];
            if (
                this.colorFormState &&
                this.colorFormState[settingKey] &&
                this.colorFormState[settingKey][type.name]
            ) {
                // get color from local storage settings if present
                color = this.colorFormState[settingKey][type.name];
            } else if (Object.hasOwn(this.defaultColors, key)) {
                // in the original baseline editor, a string was added to an integer to get
                // this number!
                color = changeHue(this.defaultColors[key], 3 * (idx.toString() + 1));
            }
            return color;
        },
        /**
         * True if the item is checked in the form
         */
        isSelected(item) {
            return this.formState &&
                this.formState[this.tab] &&
                this.formState[this.tab].some((formItem) => formItem.pk === item.pk);
        },
        /**
         * Set the type's color on the color form state
         */
        setTypeColor(e, item) {
            const color = e.target.value;
            const settingKey = this.settingKeys[this.tab];
            // store by name for backwards compatibility
            this.colorFormState[settingKey][item.name] = color;
        },
    },
}
</script>
