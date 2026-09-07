<template>
    <ul>
        <li
            v-for="task in taskStatuses"
            :key="task.pk"
        >
            <div
                :class="{
                    'escr-spinner': ['Queued', 'Initiated'].includes(task.label),
                    [`escr-spinner--${task.icon}`]: ['Queued', 'Initiated'].includes(task.label),
                    [`escr-status--${task.icon}`]: !['Queued', 'Initiated'].includes(task.label),
                }"
                role="status"
            >
                <CheckCircleFilledIcon v-if="['complete', 'warning'].includes(task.icon)" />
                <ErrorIcon v-else-if="task.icon === 'error'" />
                <CanceledIcon v-else-if="task.label === 'Canceled'" />
                <span class="sr-only">{{ task.status }}</span>
            </div>
            <div class="meta">
                <span class="task-label">{{ task.method }}</span>
                <span>{{ task.message }}</span>
                <span class="timestamp">
                    {{ task.label }} {{ task.timestamp }}
                </span>
            </div>
            <EscrButton
                v-if="['Queued', 'Initiated'].includes(task.label)"
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
</template>
<script>
import { mapActions, mapState } from "vuex";
import CancelIcon from "../../components/Icons/CancelIcon/CancelIcon.vue";
import CanceledIcon from "../../components/Icons/CanceledIcon/CanceledIcon.vue";
// eslint-disable-next-line max-len
import CheckCircleFilledIcon from "../../components/Icons/CheckCircleFilledIcon/CheckCircleFilledIcon.vue";
import ErrorIcon from "../../components/Icons/ErrorIcon/ErrorIcon.vue";
import EscrButton from "../../components/Button/Button.vue";

export default {
    name: "EscrTaskDashboard",
    components: { CancelIcon, CanceledIcon, CheckCircleFilledIcon, ErrorIcon, EscrButton },
    computed: {
        ...mapState({
            taskGroups: (state) => state.document.tasks,
        }),
        taskStatuses() {
            return this.taskGroups.slice(0, 3).map((taskGroup) => {
                const { tasks, method } = taskGroup;
                const taskStatus = this.getWorkflowStatus(tasks, method);
                // convert timestamp date to string
                taskStatus.timestamp = taskStatus.timestamp
                    ? new Date(taskStatus.timestamp).toLocaleString(undefined, {
                        year: "numeric",
                        month: "numeric",
                        day: "numeric",
                        hour: "numeric",
                        minute: "2-digit",
                    })
                    : "";
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
        /**
         * Convert the task group into a single status object, which should match
         * one of the frontend statuses: Queued, Initiated, Error, Completed, Canceled.
         * It will also specify the status icon, a label for the type of task,
         * a brief message about the current status, and which timestamp to use.
         */
        getWorkflowStatus(states, method, page_count) {
            let taskStatus = {};
            // get a total count of all states
            const totalCount = states.reduce((acc, t) => acc + t.count, 0);
            const elementCount = page_count != null ? page_count : totalCount;
            // generate a string for the task label (method)
            let m = method.split(".").pop();
            if (["segment", "transcribe"].includes(m)) {
                // these two taskgroups have one task per element
                m = `${m} ${elementCount} Element${elementCount > 1 ? "s" : ""}`;
            }
            if (m === "segtrain") {
                taskStatus.method = "Train Segmenter Model";
            } else if (m === "train") {
                taskStatus.method = "Train Recognizer Model";
            } else {
                taskStatus.method = m.charAt(0).toUpperCase() + m.slice(1);
            }
            // convert to an object where keys are workflow state
            const stateObj = states.reduce(
                (obj, item) => (obj[item.workflow_state] = item, obj), {}
            );
            // get icon, message, label, timestamp depending on mixed state
            if (stateObj["Canceled"]) {
                taskStatus.label = "Canceled";
                taskStatus.icon = "inactive";
                taskStatus.message = "Canceled";
                taskStatus.timestamp = stateObj["Canceled"].done_at;
            } else if (stateObj["Finished"]) {
                taskStatus.label = "Completed";
                taskStatus.icon = "complete";
                taskStatus.message = `${stateObj["Finished"].count}/${totalCount} complete`;
                taskStatus.timestamp = stateObj["Finished"].done_at;
                if (stateObj["Queued"] || stateObj["Running"]) {
                    taskStatus.label = "Initiated";
                    taskStatus.icon = "secondary";
                    taskStatus.timestamp = stateObj["Queued"]
                        ? stateObj["Queued"].queued_at
                        : stateObj["Running"].started_at;
                } else if (stateObj["Crashed"]) {
                    taskStatus.message = `Completed, ${
                        stateObj["Crashed"].count
                    }/${totalCount} errors`;
                    taskStatus.icon = "warning";
                }
            } else if (stateObj["Running"]) {
                taskStatus.label = "Initiated";
                taskStatus.icon = "secondary";
                taskStatus.message = "In progress";
                taskStatus.timestamp = stateObj["Running"].started_at;
            } else if (stateObj["Queued"]) {
                taskStatus.label = "Queued";
                taskStatus.icon = "inactive";
                taskStatus.message = "Waiting...";
                taskStatus.timestamp = stateObj["Queued"].queued_at;
            } else if (stateObj["Crashed"]) {
                taskStatus.label = "Completed";
                taskStatus.icon = "error";
                taskStatus.message = "Error";
                taskStatus.timestamp = stateObj["Crashed"].done_at;
            }
            return taskStatus;
        },
    }
}
</script>
