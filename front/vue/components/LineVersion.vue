<template>
    <div class="d-table-row pt-1">
        <div
            class="d-table-cell w-100"
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
                class="btn btn-sm btn-info js-pull-state"
                title="Load this state"
                @click="loadState"
            >
                <i class="fas fa-file-upload" />
            </button>
        </div>
    </div>
</template>

<script>
export default Vue.extend({
    props: ["version", "previous", "line"],
    computed: {
        momentDate() {
            return moment.tz(this.version.created_at, this.timeZone).calendar();
        },
        versionContent() {
            if (this.version.data) {
                return this.version.data.content;
            }
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

<style scoped>
</style>
