<template>
    <VMenu
        placement="bottom-end"
        theme="vertical-menu"
        :distance="8"
        :shown="isOpen"
        :triggers="[]"
        :auto-hide="true"
        @apply-hide="close"
    >
        <EscrButton
            :on-click="open"
            :class="{
                ['escr-compare-dropdown']: true,
                placeholder: !comparedTranscriptions.length
            }"
            size="small"
            color="text"
            :label="comparedTranscriptions.length
                ? `${comparedTranscriptions.length} selected`
                : 'Select'"
        >
            <template #button-icon>
                <TranscribeIcon />
            </template>
            <template #button-icon-right>
                <ChevronDownIcon />
            </template>
        </EscrButton>
        <template #popper>
            <div class="escr-transcription-selector">
                <div class="selector-header">
                    <h3>Transcriptions</h3>
                    <div>
                        <EscrButton
                            label="Select All"
                            color="link-primary"
                            size="small"
                            :on-click="selectAll"
                            :disabled="comparedTranscriptions.length === allTranscriptions.length"
                        />
                        <EscrButton
                            label="Select None"
                            color="link-primary"
                            size="small"
                            :on-click="selectNone"
                            :disabled="comparedTranscriptions.length === 0"
                        />
                    </div>
                </div>
                <ul>
                    <li
                        v-for="transcription in allTranscriptionsSorted"
                        :key="transcription.pk"
                    >
                        <label>
                            <input
                                type="checkbox"
                                :checked="comparedTranscriptions.includes(
                                    parseInt(transcription.pk)
                                )"
                                @change="(e) => toggleTranscription(
                                    parseInt(transcription.pk),
                                    e.target.checked,
                                )"
                            >
                            <span>{{ transcription.name }}</span>
                        </label>
                    </li>
                </ul>
            </div>
        </template>
    </VMenu>
</template>
<script>
import { mapMutations, mapState } from "vuex";
import { Menu as VMenu } from "floating-vue";
import ChevronDownIcon from "../Icons/ChevronDownIcon/ChevronDownIcon.vue";
import EscrButton from "../Button/Button.vue";
import TranscribeIcon from "../Icons/TranscribeIcon/TranscribeIcon.vue";
import "./TranscriptionSelector.css";

export default {
    name: "EscrTranscriptionSelector",
    components: {
        ChevronDownIcon,
        EscrButton,
        TranscribeIcon,
        VMenu,
    },
    data() {
        return {
            isOpen: false,
        };
    },
    computed: {
        ...mapState({
            allTranscriptions: (state) => state.transcriptions.all,
            comparedTranscriptions: (state) => state.transcriptions.comparedTranscriptions,
        }),
        /**
         * Sort the list of all transcriptions by PK
         */
        allTranscriptionsSorted() {
            return this.allTranscriptions.toSorted((a, b) => {
                return parseInt(a.pk) - parseInt(b.pk);
            });
        },
    },
    methods: {
        ...mapMutations("transcriptions", [
            "addComparedTranscription",
            "removeComparedTranscription",
            "setComparedTranscriptions",
        ]),
        /**
         * Close this dialog
         */
        close() {
            this.isOpen = false;
        },
        /**
         * Open this dialog
         */
        open() {
            this.isOpen = true;
        },
        /**
         * Select all transcriptions for comparison
         */
        selectAll() {
            const allPks = this.allTranscriptions.map((transcription) => {
                return parseInt(transcription.pk);
            });
            this.setComparedTranscriptions(allPks);
        },
        /**
         * Deselect all transcriptions for comparison
         */
        selectNone() {
            this.setComparedTranscriptions([]);
        },
        /**
         * Handle check and uncheck transcriptions for comparison
         */
        toggleTranscription(pk, select) {
            if (select && !this.comparedTranscriptions.includes(pk)) {
                this.addComparedTranscription(pk);
            } else if (!select && this.comparedTranscriptions.includes(pk)) {
                this.removeComparedTranscription(pk);
            }
        },
    }
}
</script>
