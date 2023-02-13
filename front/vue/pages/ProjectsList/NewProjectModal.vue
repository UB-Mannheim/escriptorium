<template>
    <EscrModal class="escr-new-project">
        <template #modal-content>
            <h2>Create New Project</h2>
            <TextField
                label="Name"
                placeholder="Enter project name"
                :on-input="onInput"
            />
        </template>
        <template #modal-actions>
            <EscrButton
                color="outline-primary"
                label="Cancel"
                :on-click="onCancel"
            />
            <EscrButton
                color="primary"
                label="Create"
                :on-click="onCreate"
                :disabled="createDisabled"
            />
        </template>
    </EscrModal>
</template>
<script>
import "./ProjectsList.css";
import EscrButton from "../../components/Button/Button.vue";
import EscrModal from "../../components/Modal/Modal.vue";
import TextField from "../../components/TextField/TextField.vue";


export default {
    name: "EscrNewProjectModal",
    components: {
        EscrButton,
        EscrModal,
        TextField,
    },
    props: {
        onCancel: {
            type: Function,
            required: true,
        },
        onCreate: {
            type: Function,
            required: true,
        },
        onInput: {
            type: Function,
            required: true,
        },
        createDisabled: {
            type: Boolean,
            default: false,
        },
    }
};
</script>
