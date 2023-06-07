<template>
    <ul v-if="!loading">
        <li
            v-for="task in taskStatuses"
            :key="task.pk"
        >
            <div
                :class="{
                    'escr-spinner': true,
                    [`escr-spinner--${task.icon}`]: true,
                }"
                role="status"
            >
                <span class="sr-only">{{ task.status }}</span>
            </div>
            <div class="meta">
                <span class="task-label">{{ task.label }}</span>
                <span>{{ task.message }}</span>
                <span>{{ task.status }} {{ task.timestamp }}</span>
            </div>
            <EscrButton
                v-if="[0, 1].includes(task.workflow_state)"
                color="text"
                size="small"
                :on-click="() => handleCancel(task)"
            >
                <template #button-icon>
                    <CancelIcon />
                </template>
            </EscrButton>
        </li>
    </ul>
    <div
        v-else
        class="escr-spinner-container"
    >
        <div
            class="escr-spinner"
            role="status"
        >
            <span class="sr-only">Loading...</span>
        </div>
    </div>
</template>
<script>
import { mapActions, mapState } from "vuex";
import CancelIcon from "../../components/Icons/CancelIcon/CancelIcon.vue";
import EscrButton from "../../components/Button/Button.vue";

export default {
    name: "EscrTaskDashboard",
    components: { CancelIcon, EscrButton },
    computed: {
        ...mapState({
            loading: (state) => state.document.loading.tasks,
            tasks: (state) => state.document.tasks,
        }),
        taskStatuses() {
            return this.tasks.slice(0, 3).map((task) => {
                const taskStatus = {
                    pk: task.pk,
                    workflow_state: task.workflow_state,
                };
                switch (task.workflow_state) {
                    case 0:
                        taskStatus.icon = "inactive";
                        taskStatus.status = "Queued";
                        taskStatus.message = "Waiting...";
                        taskStatus.timestamp = task.queued_at;
                        break;
                    case 1:
                        taskStatus.icon = "secondary";
                        taskStatus.status = "Initiated";
                        taskStatus.message = "In Progress";
                        taskStatus.timestamp = task.started_at;
                        break;
                    case 2:
                        taskStatus.icon = "danger";
                        taskStatus.status = "Error";
                        taskStatus.message = "Error";
                        taskStatus.timestamp = task.done_at;
                        break;
                    case 3:
                        taskStatus.icon = "secondary-inactive";
                        taskStatus.status = "Completed";
                        taskStatus.message = "Complete";
                        taskStatus.timestamp = task.done_at;
                        break;
                    case 4:
                        taskStatus.icon = "inactive";
                        taskStatus.status = "Canceled";
                        taskStatus.message = "Canceled";
                        taskStatus.timestamp = task.done_at;
                        break;
                    default:
                        break;
                }
                const options = {
                    year: "numeric",
                    month: "numeric",
                    day: "numeric",
                    hour: "numeric",
                    minute: "2-digit",
                };
                taskStatus.timestamp = taskStatus.timestamp
                    ? new Date(taskStatus.timestamp).toLocaleString(undefined, options)
                    : "";
                taskStatus.label = task.document_part
                    ? `${task.label.split(" ")[0]} ${task.document_part}`
                    : task.label;
                return taskStatus;
            });
        },
    },
    methods: {
        ...mapActions("tasks", ["openModal", "selectTask"]),
        handleCancel(task) {
            this.selectTask(task);
            this.openModal("cancelWarning");
        },
    }
}
</script>
