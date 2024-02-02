<template>
    <div
        :class="{
            ['d-table-row']: true,
            ['pt-1']: legacyModeEnabled,
            ['escr-line-version']: !legacyModeEnabled,
        }"
    >
        <div
            class="d-table-cell w-100 escr-line-content"
            :title="version.data.content"
            v-html="versionCompare"
        />
        <div
            class="d-table-cell"
            title="Edited by author (source)"
        >
            {{ version.author }} ( {{ version.source }} )
        </div>
        <div
            class="d-table-cell"
            title="Edited on"
        >
            {{ momentDate }}
        </div>
        <div class="d-table-cell">
            <button
                v-if="legacyModeEnabled"
                class="btn btn-sm btn-info js-pull-state"
                title="Load this state"
                @click="loadState"
            >
                <i class="fas fa-file-upload" />
            </button>
            <EscrButton
                v-else
                size="small"
                color="text-alt"
                :on-click="loadState"
            >
                <template #button-icon>
                    <HistoryIcon />
                </template>
            </EscrButton>
        </div>
    </div>
</template>

<script>
import EscrButton from "./Button/Button.vue";
import HistoryIcon from "./Icons/HistoryIcon/HistoryIcon.vue";

export default Vue.extend({
    components: {
        EscrButton,
        HistoryIcon,
    },
    props: {
        version: {
            type: Object,
            required: true,
        },
        previous: {
            type: Object,
            default: null,
        },
        /**
         * Whether or not legacy mode is enabled by the user.
         */
        legacyModeEnabled: {
            type: Boolean,
            default: true,
        },
    },
    computed: {
        momentDate() {
            return moment.tz(this.version.created_at, this.timeZone).calendar();
        },
        versionContent() {
            if (this.version.data) {
                return this.version.data.content;
            }
            return "";
        },
        versionCompare() {
            if (this.version.data) {
                if (!this.previous) return this.version.data.content;
                let diff = Diff.diffChars(this.previous.data.content, this.version.data.content);
                return diff.map(function(part){
                    if (part.removed) {
                        return '<span class="cmp-del">'+part.value+"</span>";
                    } else if (part.added) {
                        return '<span class="cmp-add">'+part.value+"</span>";
                    } else {
                        return part.value;
                    }
                }.bind(this)).join("");
            }
            return "";
        }
    },
    created() {
        this.timeZone = this.$parent.timeZone;
    },
    beoforeDestroy() {
        this.timeZone = null;  // make sure it's garbage collected
    },
    methods: {
        async loadState() {
            this.$parent.localTranscription = this.version.data.content;
        },
    }
});
</script>
