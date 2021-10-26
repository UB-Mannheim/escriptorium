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
            <TextField
                placeholder="Enter username of registered user"
                label="Add user"
                :label-visible="false"
                :on-input="handleUserInput"
                :disabled="disabled"
                :value="username"
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
import EscrButton from "../Button/Button.vue";
import EscrDropdown from "../Dropdown/Dropdown.vue";
import EscrModal from "../Modal/Modal.vue";
import TextField from "../TextField/TextField.vue";
import XIcon from "../Icons/XIcon/XIcon.vue";
import "./ShareModal.css";

export default {
    name: "EscrShareModal",
    components: {
        EscrButton,
        EscrDropdown,
        EscrModal,
        TextField,
        XIcon,
    },
    props: {
        disabled: {
            type: Boolean,
            default: false,
        },
        groups: {
            type: Array,
            default: () => [],
        },
        onCancel: {
            type: Function,
            required: true,
        },
        onSubmit: {
            type: Function,
            required: true,
        },
    },
    computed: {
        ...mapState({
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
    },
    methods: {
        ...mapActions("forms", ["clearForm", "handleTextInput"]),
        handleGroupChange(e) {
            if (this.username !== "") {
                this.handleTextInput({ form: "share", field: "user", value: "" });
            }
            this.handleTextInput({ form: "share", field: "group", value: e.target.value });
        },
        handleUserInput(e) {
            if (this.selectedGroup !== "") {
                this.handleTextInput({ form: "share", field: "group", value: "" });
            }
            this.handleTextInput({ form: "share", field: "user", value: e.target.value });
        },
    },
}
</script>