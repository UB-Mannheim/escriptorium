<template>
    <EscrModal
        class="escr-share-modal"
    >
        <template #modal-header>
            <h2>Add Group or User</h2>
            <EscrButton
                color="text"
                :on-click="onCancel"
                size="small"
            >
                <template #button-icon>
                    <XIcon />
                </template>
            </EscrButton>
        </template>
        <template #modal-content>
            <h3>Add Group</h3>
            <EscrDropdown
                label="Add group"
                :disabled="disabled || !groups"
                :options="groupOptions"
                :on-change="handleGroupChange"
            />
            <h3>Add User</h3>
            <EscrAutocompleteDropdown
                :key="userFieldKey"
                placeholder="Enter username of registered user"
                label="Add user"
                :allow-custom-value="true"
                :matches-only="true"
                :option-groups="userOptionGroups"
                :on-change="handleUserInput"
                :disabled="disabled"
            />
        </template>
        <template #modal-actions>
            <EscrButton
                color="outline-primary"
                label="Cancel"
                :on-click="onCancel"
                :disabled="disabled"
            />
            <EscrButton
                color="primary"
                label="Submit"
                :on-click="onSubmit"
                :disabled="disabled || (!selectedGroup && !username)"
            />
        </template>
    </EscrModal>
</template>
<script>
import { mapActions, mapState } from "vuex";
import EscrAutocompleteDropdown from "../AutocompleteDropdown/AutocompleteDropdown.vue";
import EscrButton from "../Button/Button.vue";
import EscrDropdown from "../Dropdown/Dropdown.vue";
import EscrModal from "../Modal/Modal.vue";
import XIcon from "../Icons/XIcon/XIcon.vue";
import "./ShareModal.css";

export default {
    name: "EscrShareModal",
    components: {
        EscrAutocompleteDropdown,
        EscrButton,
        EscrDropdown,
        EscrModal,
        XIcon,
    },
    props: {
        /**
         * Boolean to indicate whether fields should be disabled.
         */
        disabled: {
            type: Boolean,
            default: false,
        },
        /**
         * Array of all of the current user's groups, each structured as follows:
         * {
         *     name: String,
         *     pk: Number,
         * }
         */
        groups: {
            type: Array,
            default: () => [],
        },
        /**
         * Callback function for cancelling the action.
         */
        onCancel: {
            type: Function,
            required: true,
        },
        /**
         * Callback function for submitting the form.
         */
        onSubmit: {
            type: Function,
            required: true,
        },
    },
    data() {
        return {
            userFieldKey: 0,
        };
    },
    computed: {
        ...mapState({
            collaborators: (state) => state.user.collaborators,
            selectedGroup: (state) => state.forms.share.group,
            username: (state) => state.forms.share.user,
        }),
        groupOptions() {
            return this.groups.map((group) => ({
                label: group.name,
                value: group.pk.toString(),
                selected: this.selectedGroup.toString() === group.pk.toString(),
            }));
        },
        userOptionGroups() {
            if (!this.collaborators.length) return [];
            return [{
                options: this.collaborators.map((name) => ({
                    label: name,
                    value: name,
                    selected: name === this.username,
                })),
            }];
        },
    },
    created() {
        this.fetchCollaborators();
    },
    methods: {
        ...mapActions("forms", ["clearForm", "handleGenericInput"]),
        ...mapActions("user", ["fetchCollaborators"]),
        handleGroupChange(e) {
            if (this.username !== "") {
                this.handleGenericInput({ form: "share", field: "user", value: "" });
                this.userFieldKey++;
            }
            this.handleGenericInput({ form: "share", field: "group", value: e.target.value });
        },
        handleUserInput(e) {
            if (this.selectedGroup !== "") {
                this.handleGenericInput({ form: "share", field: "group", value: "" });
            }
            this.handleGenericInput({ form: "share", field: "user", value: e.target.value });
        },
    },
}
</script>
