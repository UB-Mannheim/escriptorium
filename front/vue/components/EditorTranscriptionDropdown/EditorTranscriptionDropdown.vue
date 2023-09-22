<template>
    <EscrDropdown
        class="escr-editor-transcription-dropdown"
        :disabled="disabled"
        :options="transcriptionLayerOptions"
        :on-change="changeTranscriptionlayer"
        label="Change the visible transcription layer"
    />
</template>
<script>
import EscrDropdown from "../Dropdown/Dropdown.vue";
import { mapMutations, mapState } from "vuex";
import "./EditorTranscriptionDropdown.css";

export default {
    name: "EscrEditorTranscriptionDropdown",
    components: {
        EscrDropdown,
    },
    props: {
        /**
         * True if the dropdown is disabled
         */
        disabled: {
            type: Boolean,
            required: true,
        }
    },
    computed: {
        ...mapState({
            allTranscriptions: (state) => state.transcriptions.all,
            selectedTranscription: (state) => state.transcriptions.selectedTranscription,
        }),
        transcriptionLayerOptions() {
            return this.allTranscriptions.filter((t) => !t.archived).map((transcription) => ({
                value: transcription.pk,
                label: transcription.name,
                selected: parseInt(this.selectedTranscription) === parseInt(transcription.pk),
            }));
        },
    },
    methods: {
        ...mapMutations("transcriptions", ["setSelectedTranscription"]),
        changeTranscriptionlayer(e) {
            this.setSelectedTranscription(parseInt(e.target.value));
        },
    }
}
</script>
