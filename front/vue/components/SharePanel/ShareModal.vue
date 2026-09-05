<template>
    <EscrModal
        class="escr-share-modal"
    >
        <template #modal-header>
            <h2 v-translate>Add Group or User</h2>
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
            <h3 v-translate>Add Group</h3>
            <EscrAutocompleteDropdown
                :label="$gettext('Add group')"
                :disabled="disabled || !groups"
                :option-groups="groupOptionGroups"
                :on-change="handleGroupChange"
            />
            <h3 v-translate>Add User</h3>
            <EscrAutocompleteDropdown
                :key="userFieldKey"
                :placeholder="$gettext('Enter username of registered user')"
                :label="$gettext('Add user')"
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
                :label="$gettext('Cancel')"
                :on-click="onCancel"
                :disabled="disabled"
            />
            <EscrButton
                color="primary"
                :label="$gettext('Submit')"
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
import EscrModal from "../Modal/Modal.vue";
import XIcon from "../Icons/XIcon/XIcon.vue";
import "./ShareModal.css";

export default {
    name: "EscrShareModal",
    components: {
        EscrAutocompleteDropdown,
        EscrButton,
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
        sharedUsers: {
            type: Array,
            default: () => [],
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
        groupOptionGroups() {
            if (!this.groups.length) return [];
            return [{
                options: this.groups.map((group) => ({
                    label: group.name,
                    value: group.pk.toString(),
                    selected: this.selectedGroup.toString() === group.pk.toString(),
                })),
            }];
        },
        userOptionGroups() {
            const shared = this.sharedUsers.map((user) => user.username);
            const users = this.collaborators.filter((user) => !shared.includes(user.username));
            if (!users.length) return [];
            return [{
                options: users.map((user) => ({
                    label: user.username,
                    value: user.username,
                    hint: [user.first_name, user.last_name].join(" ").trim(),
                    selected: user.username === this.username,
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
            if (e.target.value && this.username !== "") {
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
