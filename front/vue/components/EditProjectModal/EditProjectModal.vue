<template>
    <EscrModal class="escr-edit-project">
        <template #modal-content>
            <div class="escr-modal-header">
                <h2>{{ newProject ? "Create New" : "Edit" }} Project</h2>
                <EscrButton
                    color="text"
                    :on-click="onCancel"
                    size="small"
                >
                    <template #button-icon>
                        <XIcon />
                    </template>
                </EscrButton>
            </div>
            <TextField
                label="Name"
                placeholder="Enter project name"
                :disabled="disabled"
                :on-input="handleNameInput"
                :value="name"
                required
            />
            <TextField
                label="Link to Project Guidelines"
                placeholder="https://"
                :disabled="disabled"
                :on-input="handleGuidelinesInput"
                :value="guidelines"
            />
            <TagsField
                label="Tags"
                :disabled="disabled"
                :on-change="handleTagsFieldInput"
                :on-change-tag-name="handleTagNameInput"
                :on-create-tag="onCreateTag"
                :tag-name="tagName"
                :tags="tags"
                :selected-tags="selectedTags"
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
                :label="newProject ? 'Create' : 'Save'"
                :on-click="onSave"
                :disabled="disabled || !name"
            />
        </template>
    </EscrModal>
</template>
<script>
import { mapActions, mapState } from "vuex";
import EscrButton from "../Button/Button.vue";
import EscrModal from "../Modal/Modal.vue";
import TagsField from "../TagsField/TagsField.vue";
import TextField from "../TextField/TextField.vue";
import "./EditProjectModal.css";
import XIcon from "../Icons/XIcon/XIcon.vue";

export default {
    name: "EscrEditProjectModal",
    components: {
        EscrButton,
        EscrModal,
        TagsField,
        TextField,
        XIcon,
    },
    props: {
        /**
         * Boolean indicating if the form fields should be disabled
         */
        disabled: {
            type: Boolean,
            default: false,
        },
        /**
         * If this is a new project, set true; if it's editing an existing one, leave false
         */
        newProject: {
            type: Boolean,
            default: false,
        },
        /**
         * Callback for clicking the cancel button
         */
        onCancel: {
            type: Function,
            required: true,
        },
        /**
         * Callback for clicking the "create tag" button
         */
        onCreateTag: {
            type: Function,
            required: true,
        },
        /**
         * Callback for clicking the save/create button
         */
        onSave: {
            type: Function,
            required: true,
        },
        /**
         * Full list of tags across all projects
         */
        tags: {
            type: Array,
            default: () => [],
        },
    },
    computed: {
        ...mapState({
            guidelines: (state) => state.forms.editProject.guidelines,
            name: (state) => state.forms.editProject.name,
            selectedTags: (state) => state.forms.editProject.tags,
            tagName: (state) => state.forms.editProject.tagName,
        }),
    },
    methods: {
        ...mapActions("forms", [
            "handleTextInput",
            "handleTagsInput",
        ]),
        handleTagsFieldInput({ checked, tag }) {
            this.handleTagsInput({ checked, tag, form: "editProject" });
        },
        handleNameInput(e) {
            this.handleTextInput({ form: "editProject", field: "name", value: e.target.value});
        },
        handleGuidelinesInput(e) {
            this.handleTextInput(
                { form: "editProject", field: "guidelines", value: e.target.value}
            );
        },
        handleTagNameInput(e) {
            this.handleTextInput({ form: "editProject", field: "tagName", value: e.target.value});
        },
    },
};
</script>
