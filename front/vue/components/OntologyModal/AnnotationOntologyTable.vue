<template>
    <div>
        <table
            v-if="types"
            class="escr-table annotation-ontology"
        >
            <thead>
                <tr>
                    <th class="name-column">
                        <div><span>Name</span></div>
                    </th>
                    <th>
                        <div><span>Button Text</span></div>
                    </th>
                    <th>
                        <div><span>Components</span></div>
                    </th>
                    <th>
                        <div><span>Type</span></div>
                    </th>
                    <th>
                        <div><span>Marker Type</span></div>
                    </th>
                    <th class="color-column">
                        <div><span>Color</span></div>
                    </th>
                    <th class="comments-column">
                        <div><span>Comments</span></div>
                    </th>
                    <th class="remove-column" />
                </tr>
            </thead>
            <tbody>
                <tr
                    v-for="item in types"
                    :key="item.pk"
                >
                    <!-- name -->
                    <td class="name-column escr-text-field">
                        <input
                            type="text"
                            :disabled="disabled"
                            :value="item.name"
                            :invalid="!item.name"
                            @input="(e) => onChange(e, 'name', item)"
                        >
                    </td>
                    <!-- abbreviation -->
                    <td class="abbreviation-column escr-text-field">
                        <input
                            type="text"
                            maxlength="3"
                            :disabled="disabled"
                            :value="item.abbreviation"
                            :invalid="!item.abbreviation"
                            @input="(e) => onChange(e, 'abbreviation', item)"
                        >
                    </td>
                    <!-- component selection -->
                    <td>
                        <VMenu
                            placement="bottom-end"
                            theme="vertical-menu"
                            :distance="8"
                            :shown="componentDropdownOpen === item.pk"
                            :triggers="[]"
                            :auto-hide="true"
                            @apply-hide="() => closeComponentDropdown(item.pk)"
                        >
                            <EscrButton
                                :on-click="() => openComponentDropdown(item.pk)"
                                :class="{
                                    ['escr-component-dropdown']: true,
                                    placeholder: !(item.components && item.components.length)
                                }"
                                size="small"
                                color="text"
                                :label="(item.components && item.components.length)
                                    ? `${item.components.length} selected`
                                    : 'Components'"
                            >
                                <template #button-icon-right>
                                    <ChevronDownIcon />
                                </template>
                            </EscrButton>
                            <template #popper>
                                <div class="escr-component-selector">
                                    <ul v-if="components && components.length">
                                        <li
                                            v-for="component in components"
                                            :key="component.pk"
                                        >
                                            <label>
                                                <input
                                                    type="checkbox"
                                                    :checked="item.components &&
                                                        item.components.some((comp) =>
                                                            comp.pk === parseInt(component.pk)
                                                        )"
                                                    @change="() => toggleComponent(item, component)"
                                                >
                                                <span>{{ component.name }}</span>
                                            </label>
                                        </li>
                                    </ul>
                                    <div
                                        v-else
                                        class="escr-no-components"
                                    >
                                        <span>No Components</span>
                                        <small>Click "Add New" to add</small>
                                    </div>
                                </div>
                                <div>
                                    <EscrButton
                                        size="small"
                                        color="text"
                                        label="Add New"
                                        :on-click="openAddComponentModal"
                                    >
                                        <template #button-icon>
                                            <PlusIcon />
                                        </template>
                                    </EscrButton>
                                </div>
                            </template>
                        </VMenu>
                    </td>
                    <!-- type -->
                    <td class="escr-text-field">
                        <input
                            type="text"
                            :disabled="disabled"
                            :value="item.newTypology || (item.typology && item.typology.name)"
                            @input="(e) => onChange(e, 'newTypology', item)"
                        >
                    </td>
                    <!-- marker type -->
                    <td>
                        <DropdownField
                            label="Marker type"
                            :disabled="disabled"
                            :options="getMarkerTypeOptions(item)"
                            :on-change="(e) => onChange(e, 'marker_type', item)"
                            :label-visible="false"
                        />
                    </td>
                    <!-- marker color -->
                    <td
                        class="color-column"
                    >
                        <input
                            type="color"
                            class="escr-color-button"
                            aria-label="select color"
                            :disabled="disabled"
                            :value="item.marker_detail"
                            @focusout="(e) => onChange(e, 'marker_detail', item)"
                        >
                    </td>
                    <!-- delete -->
                    <td class="comments-column">
                        <label
                            class="comments-toggle"
                            :disabled="disabled"
                        >
                            <input
                                type="checkbox"
                                class="sr-only"
                                :disabled="disabled"
                                :checked="item.has_comments"
                                @change="(e) => onToggleComments(e, item)"
                            >
                            <ToggleOnIcon v-if="item.has_comments" />
                            <ToggleOffIcon v-else />
                        </label>
                    </td>
                    <!-- delete -->
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
        <EscrModal
            v-if="addComponentModalOpen"
            class="escr-add-component"
        >
            <template #modal-header>
                <h2>Add New Component</h2>
                <EscrButton
                    color="text"
                    :on-click="closeAddComponentModal"
                    size="small"
                >
                    <template #button-icon>
                        <XIcon />
                    </template>
                </EscrButton>
            </template>
            <template #modal-content>
                <TextField
                    label="Name"
                    placeholder="Name"
                    :disabled="disabled"
                    :on-input="(e) => handleGenericInput({
                        form: 'addComponent', field: 'name', value: e.target.value
                    })"
                    :value="addComponentForm.name"
                    required
                />
                <TextField
                    help-text="Comma-separated list of accepted values for this component"
                    label="Allowed Values"
                    placeholder="Allowed Values"
                    :disabled="disabled"
                    :on-input="(e) => handleGenericInput({
                        form: 'addComponent', field: 'values', value: e.target.value
                    })"
                    :value="addComponentForm.values"
                    required
                />
            </template>
            <template #modal-actions>
                <EscrButton
                    color="outline-primary"
                    label="Cancel"
                    :disabled="disabled"
                    :on-click="closeAddComponentModal"
                />
                <EscrButton
                    color="primary"
                    label="Add"
                    :disabled="disabled"
                    :on-click="onAddComponent"
                />
            </template>
        </EscrModal>
    </div>
</template>
<script>
import { Menu as VMenu } from "floating-vue";
import { mapActions, mapState } from "vuex";
import ChevronDownIcon from "../Icons/ChevronDownIcon/ChevronDownIcon.vue";
import DropdownField from "../Dropdown/DropdownField.vue";
import EscrButton from "../Button/Button.vue";
import EscrModal from "../Modal/Modal.vue";
import PlusIcon from "../Icons/PlusIcon/PlusIcon.vue";
import TextField from "../TextField/TextField.vue";
import ToggleOffIcon from "../Icons/ToggleOffIcon/ToggleOffIcon.vue";
import ToggleOnIcon from "../Icons/ToggleOnIcon/ToggleOnIcon.vue";
import XIcon from "../Icons/XIcon/XIcon.vue";
import "./AnnotationOntologyTable.css";

export default {
    name: "AnnotationOntologyTable",
    components: {
        ChevronDownIcon,
        DropdownField,
        EscrButton,
        EscrModal,
        PlusIcon,
        TextField,
        ToggleOffIcon,
        ToggleOnIcon,
        VMenu,
        XIcon,
    },
    props: {
        /**
         * True if all buttons and form fields should be disabled
         */
        disabled: {
            type: Boolean,
            required: true,
        },
        /**
         * Callback for removing an item
         */
        onRemoveType: {
            type: Function,
            required: true,
        },
        /**
         * Current tab (i.e. whether these are image or text annotations)
         */
        tab: {
            type: String,
            required: true,
        },
        /**
         * All annotation types (from the form state)
         */
        types: {
            type: Array,
            required: true,
        },
    },
    data() {
        return {
            addComponentModalOpen: false,
            componentDropdownOpen: null,
        };
    },
    computed: {
        ...mapState({
            addComponentForm: (state) => state.forms.addComponent,
            components: (state) => state.document.componentTaxonomies,
        }),
    },
    methods: {
        ...mapActions("document", ["createComponent"]),
        ...mapActions("forms", ["clearForm", "handleGenericInput", "handleGenericArrayInput"]),
        /**
         * Close the "add new component" modal and clear its state
         */
        closeAddComponentModal() {
            this.addComponentModalOpen = false;
            this.clearForm("addComponent");
        },
        /**
         * Close the component selector dropdown
         */
        closeComponentDropdown(pk) {
            if (this.componentDropdownOpen === pk) {
                this.componentDropdownOpen = null;
            }
        },
        /**
         * Populate the marker type dropdown, including which element is selected, for an item
         */
        getMarkerTypeOptions(item) {
            return [
                {
                    label: "Background Color",
                    value: "Background Color",
                    selected: item.marker_type === "Background Color",
                },
                {
                    label: "Text Color",
                    value: "Text Color",
                    selected: item.marker_type === "Text Color",
                },
                { label: "Bold", value: "Bold", selected: item.marker_type === "Bold" },
                { label: "Italic", value: "Italic", selected: item.marker_type === "Italic" },
            ];
        },
        /**
         * Callback to create a new component
         */
        async onAddComponent() {
            await this.createComponent();
            this.closeAddComponentModal();
        },
        /**
         * Generic form fields event handler
         */
        onChange(e, field, item) {
            const value = structuredClone(item);
            value[field] = e.target.value;
            this.handleGenericArrayInput({
                form: "ontology", field: this.tab, action: "update", value
            });
        },
        /**
         * Handler for toggling comments on and off for an item
         */
        onToggleComments(e, item) {
            const value = structuredClone(item);
            value["has_comments"] = e.target.checked;
            this.handleGenericArrayInput({
                form: "ontology", field: this.tab, action: "update", value
            });
        },
        /**
         * Open the component selector dropdown for a specific item
         */
        openComponentDropdown(pk) {
            this.componentDropdownOpen = pk;
        },
        /**
         * Open the "add new component" modal
         */
        openAddComponentModal() {
            this.componentDropdownOpen = null;
            this.addComponentModalOpen = true;
        },
        /**
         * Handler for toggling a component choice on and off for an item
         */
        toggleComponent(item, component) {
            const value = structuredClone(item);
            const componentIndex = value.components.findIndex((c) => c.pk === component.pk)
            if (componentIndex === -1) {
                value.components.push(component);
            } else {
                value.components.splice(componentIndex, 1);
            }
            this.handleGenericArrayInput({
                form: "ontology", field: this.tab, action: "update", value
            });
        }
    }
}
</script>
