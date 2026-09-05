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
        <span
            v-else
            class="status"
            v-translate
        >
            Not initiated
        </span>
    </div>
</template>
<script>
export default {
    name: "ImageWorkflowStatus",
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
    },
    props: {
        status: {
            type: String,
            default: "",
        }
    }
}
</script>
