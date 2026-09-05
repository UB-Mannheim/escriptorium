<template>
    <EscrModal class="escr-edit-project">
        <template #modal-header>
            <h2>{{ headerText }}</h2>
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
            <TextField
                :label="$gettext('Name')"
                :placeholder="$gettext('Enter project name')"
                :disabled="disabled"
                :max-length="512"
                :on-input="(e) => handleTextFieldInput('name', e.target.value)"
                :value="name"
                required
            />
            <TextField
                :label="$gettext('Link to Project Guidelines')"
                placeholder="https://"
                :disabled="disabled"
                :on-input="(e) => handleTextFieldInput('guidelines', e.target.value)"
                :value="guidelines"
                :invalid="!!guidelines && !isHttpUrl(guidelines)"
            />
            <span
                v-if="guidelines && !isHttpUrl(guidelines)"
                class="escr-help-text escr-error-text"
                v-translate
            >Must be a valid URL starting with http:// or https://.</span>
            <DropdownField
                :label="$gettext('Transcription Font')"
                :help-text="$gettext('Font used to display transcription text for documents in this project, unless overridden at the document level. Leave as Default to inherit from the user or built-in font.')"
                :disabled="disabled"
                :on-change="(e) => handleTextFieldInput('transcriptionFont', e.target.value)"
                :options="fontOptions"
            />
            <TagsField
                :label="$gettext('Tags')"
                :disabled="disabled"
                :on-change="handleTagsFieldInput"
                :on-change-tag-name="(e) => handleTextFieldInput('tagName', e.target.value)"
                :on-create-tag="onCreateTag"
                :tag-name="tagName"
                :tags="tags"
                :selected-tags="selectedTags"
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
                :label="newProject ? $gettext('Create') : $gettext('Save')"
                :on-click="onSave"
                :disabled="disabled || invalid"
            />
        </template>
    </EscrModal>
</template>
<script>
import { mapActions, mapState } from "vuex";
import DropdownField from "../Dropdown/DropdownField.vue";
import EscrButton from "../Button/Button.vue";
import EscrModal from "../Modal/Modal.vue";
import TagsField from "../TagsField/TagsField.vue";
import TextField from "../TextField/TextField.vue";
import XIcon from "../Icons/XIcon/XIcon.vue";
import "./EditProjectModal.css";

export default {
    name: "EscrEditProjectModal",
    components: {
        DropdownField,
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
        /** list of available fonts from the api */
        fonts: {
            type: Array,
            default: () => [],
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
            transcriptionFont: (state) => state.forms.editProject.transcriptionFont,
        }),
        invalid() {
            return !this.name || (!!this.guidelines && !this.isHttpUrl(this.guidelines));
        },
        /**
         * Title of the modal header, e.g. "Create New Project" or "Edit Project".
         */
        headerText() {
            return this.$gettextInterpolate(
                this.$gettext("%{action} Project"),
                { action: this.newProject ? this.$gettext("Create New") : this.$gettext("Edit") },
            );
        },
        /** dropdown options for transcription font, with a leading "Default" entry */
        fontOptions() {
            const selectedFont = this.transcriptionFont
                ? this.transcriptionFont.toString()
                : "";
            return [
                {
                    value: "",
                    label: this.$gettext("Default"),
                    selected: !selectedFont,
                },
                ...this.fonts.map((font) => ({
                    value: font.pk.toString(),
                    label: font.name,
                    selected: font.pk.toString() === selectedFont,
                })),
            ];
        },
    },
    methods: {
        ...mapActions("forms", [
            "handleGenericInput",
            "handleTagsInput",
        ]),
        handleTagsFieldInput({ checked, tag }) {
            this.handleTagsInput({ checked, tag, form: "editProject" });
        },
        handleTextFieldInput(field, value) {
            this.handleGenericInput({ form: "editProject", field, value });
        },
        isHttpUrl(string) {
            let givenURL;
            try {
                givenURL = new URL(string);
            } catch (error) {
                return false;
            }
            return givenURL.protocol === "http:" || givenURL.protocol === "https:";
        },
    },
};
</script>
