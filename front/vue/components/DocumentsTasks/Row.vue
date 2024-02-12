<template>
    <tr>
        <td>
            <input
                v-model="selected"
                class="ml-0"
                type="checkbox"
            >
        </td>
        <td>{{ documentTasks.name }}</td>
        <td>{{ documentTasks.owner }}</td>
        <td>{{ documentTasks.tasks_stats | formatStats }}</td>
        <td>{{ documentTasks.last_started_task | formatDate(timezone) }}</td>
        <td>
            <button
                data-toggle="modal"
                :data-target="'#' + modalId"
                title="Cancel pending/running tasks for this document"
                class="btn btn-danger"
            >
                Cancel
            </button>
        </td>
        <CancelModal
            :id="modalId"
            :documents-tasks="[documentTasks]"
            v-on="$listeners"
        />
    </tr>
</template>

<script>
import CancelModal from "./CancelModal.vue";

export default {
    components: {
        CancelModal,
    },
    filters: {
        formatDate(rawDate, timezone) {
            if (!rawDate) return "/";
            return moment.tz(rawDate, timezone).fromNow();
        },
        formatStats(rawStats) {
            if (!rawStats) return "/";
            const allStrings = Object.entries(rawStats).map((stat) => stat[1] !== 0 ? `${stat[1]} ${stat[0].toLowerCase()}` : null)
            const filteredStrings = allStrings.filter((val) => val)
            return filteredStrings.join(", ")
        },
    },
    props: [
        "documentTasks",
        "timezone",
        "selectAll"
    ],
    data() {
        return {
            selected: false,
        }
    },
    computed: {
        modalId () {
            return `cancelTasksModal${this.documentTasks.pk}`
        }
    },
    watch: {
        selectAll: {
            immediate: true,
            handler: function(n, o) {
                this.selected = n
            },
        },
        selected: function(n, o) {
            if (n) {
                this.$emit("selected", this.documentTasks, "add")
            } else {
                this.$emit("selected", this.documentTasks, "remove")
            }
        },
    },
};
</script>

<style scoped>
</style>
