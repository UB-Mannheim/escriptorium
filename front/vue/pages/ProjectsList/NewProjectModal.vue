<template>
    <div class="escr-modal escr-new-project">
        <h2>Create New Project</h2>
        <TextField
            label="Name"
            placeholder="Enter project name"
            :on-input="onInput"
        />
        <div class="modal-actions">
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
        </div>
    </div>
</template>
<script>
import "../../components/Common/Modal.css";
import "./ProjectsList.css";
import EscrButton from "../../components/Button/Button.vue";
import TextField from "../../components/TextField/TextField.vue";


export default {
    name: "EscrNewProjectModal",
    components: {
        EscrButton,
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
