<template>
    <div class="task-metadata">
        <span
            v-if="status.length"
            :class="{
                [status]: true,
                status: true,
            }"
        >
            {{ workflowLabel(status) }}
        </span>
        <!-- $gettext(), not v-translate: text changes after mount (see AGENTS.md) -->
        <span
            v-else
            class="status"
        >
            {{ $gettext("Not initiated") }}
        </span>
    </div>
</template>
<script>
export default {
    name: "ImageWorkflowStatus",
    props: {
        status: {
            type: String,
            default: "",
        }
    },
    methods: {
        workflowLabel(state) {
            switch (state) {
                case "pending":
                    return this.$gettext("Initiated");
                case "ongoing":
                    return this.$gettext("In Progress");
                case "error":
                    return this.$gettext("Error");
                case "done":
                    return this.$gettext("Completed");
                default:
                    return this.$gettext("Not initiated");
            }
        },
    }
}
</script>
