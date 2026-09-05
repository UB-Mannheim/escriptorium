<template>
    <div class="docstasks-list">
        <div class="row">
            <div class="col">
                <div class="form-group">
                    <label>Task state</label>
                    <select
                        v-model="selectedState"
                        class="form-control"
                    >
                        <option value="">
                            All
                        </option>
                        <option
                            v-for="[key, label] in Object.entries(taskStates)"
                            :key="key"
                            :value="label"
                        >
                            {{ label }}
                        </option>
                    </select>
                </div>
            </div>

            <div
                v-if="isAdmin"
                class="col"
            >
                <div class="form-group">
                    <label>User</label>
                    <select
                        v-model="selectedUser"
                        class="form-control"
                    >
                        <option value="">
                            All
                        </option>
                        <option
                            v-for="[id, name] in sortedUsersEntries"
                            :key="id"
                            :value="id"
                        >
                            {{ name }}
                        </option>
                    </select>
                </div>
            </div>

            <div class="col">
                <div class="form-group">
                    <label>Document name</label>
                    <input
                        v-model="documentName"
                        type="text"
                        class="form-control"
                        placeholder="Name..."
                    >
                </div>
            </div>
        </div>

        <button
            class="btn btn-primary mb-4"
            @click="getDocumentTasks"
        >
            Filter results
        </button>

        <EscrTable
            v-if="results.length"
            item-key="pk"
            actions-header="Actions"
            select-all-title="Select all documents with pending or running tasks"
            :headers="headers"
            :items="results"
            :selectable="true"
            :selected-items="selectedItems"
            :selectable-items="selectableItems"
            :on-select-all="onSelectAll"
            :on-toggle-selected="onToggleSelected"
            :on-sort="onSort"
        >
            <template #actions="{ item }">
                <EscrButton
                    v-if="hasActiveTasks(item)"
                    label="Cancel"
                    size="small"
                    color="danger"
                    title="Cancel pending/running tasks for this document"
                    :on-click="() => openCancelModal(item)"
                />
            </template>
        </EscrTable>
        <EscrLoader
            v-else
            :loading="false"
            no-data-message="No document tasks to display."
        />

        <template v-for="item in results">
            <CancelModal
                v-if="hasActiveTasks(item)"
                :key="'cancelTasksModal' + item.pk"
                :id="'cancelTasksModal' + item.pk"
                :documents-tasks="[item]"
                @cancel-success="cancelSucceeded"
                @cancel-error="cancelFailed"
            />
        </template>

        <ul class="pagination justify-content-end">
            <li class="page-item">
                <a
                    v-if="hasPrevious"
                    class="page-link"
                    @click="loadPrev()"
                ><span aria-hidden="true">&lsaquo;</span></a>
            </li>
            <li class="page-item">
                <a
                    v-if="hasNext"
                    class="page-link"
                    @click="loadNext()"
                ><span aria-hidden="true">&rsaquo;</span></a>
            </li>
        </ul>

        <EscrButton
            label="Cancel all selected"
            size="small"
            color="danger"
            title="Cancel pending/running tasks for the selected documents"
            :disabled="!Object.values(selectedList).length"
            :on-click="() => openCancelAllModal()"
        />

        <CancelModal
            id="cancelTasksModal"
            :documents-tasks="Object.values(selectedList)"
            @cancel-success="cancelSucceeded"
            @cancel-error="cancelFailed"
        />
    </div>
</template>

<script>
import CancelModal from "./CancelModal.vue";
import EscrButton from "../Button/Button.vue";
import EscrLoader from "../Loader/Loader.vue";
import EscrTable from "../Table/Table.vue";

export default {
    components: {
        CancelModal,
        EscrButton,
        EscrLoader,
        EscrTable,
    },
    props: {
        isAdmin: Boolean,
        taskStates: Object,
        users: Object,
    },
    data() {
        return {
            currentPage: 1,
            selectedState: "",
            selectedUser: "",
            documentName: "",
            selectedList: {},
            sortState: {
                value: "",
                direction: 0,
            },
        }
    },
    computed: {
        results() {
            return (this.$store.state.documentsTasks
                && this.$store.state.documentsTasks.results) || [];
        },
        hasPrevious() {
            return !!(this.$store.state.documentsTasks
                && this.$store.state.documentsTasks.previous);
        },
        hasNext() {
            return !!(this.$store.state.documentsTasks
                && this.$store.state.documentsTasks.next);
        },
        selectedItems() {
            return Object.keys(this.selectedList).map((pk) => parseInt(pk));
        },
        selectableItems() {
            return this.results
                .filter((item) => this.hasActiveTasks(item))
                .map((item) => item.pk);
        },
        sortedUsersEntries () {
            return Object.entries(this.users).sort(([, a], [, b]) => {
                a = a.toLowerCase();
                b = b.toLowerCase();
                if (a < b) return -1;
                if (a > b) return 1;
                return 0;
            })
        },
        headers() {
            return [
                { label: "Name", value: "name", sortable: true },
                { label: "User", value: "owner", sortable: true },
                { label: "Statistics", value: "tasks_stats", format: this.formatStats },
                {
                    label: "Last task started",
                    value: "last_started_task",
                    format: this.formatDate,
                    sortable: true,
                },
            ];
        },
    },
    async created() {
        this.timezone = moment.tz.guess();
        this.getDocumentTasks();
    },
    methods: {
        cancelSucceeded(messages) {
            messages.forEach((message, i) => Alert.add(`cancel-succeeded-${i}-${Date.now()}`, message, "success"))
            this.getDocumentTasks()
        },
        cancelFailed(messages) {
            messages.forEach((message, i) => Alert.add(`cancel-failed-${i}-${Date.now()}`, message, "danger"))
        },
        openCancelModal(documentTasks) {
            $(`#cancelTasksModal${documentTasks.pk}`).modal("show");
        },
        openCancelAllModal() {
            $("#cancelTasksModal").modal("show");
        },
        hasActiveTasks(documentTasks) {
            const stats = documentTasks.tasks_stats || {}
            return (stats.Queued || 0) > 0 || (stats.Running || 0) > 0
        },
        formatStats(rawStats) {
            if (!rawStats) return "/";
            const allStrings = Object.entries(rawStats).map((stat) => stat[1] !== 0 ? `${stat[1]} ${stat[0].toLowerCase()}` : null)
            const filteredStrings = allStrings.filter((val) => val)
            return filteredStrings.join(", ")
        },
        formatDate(rawDate) {
            if (!rawDate) return "/";
            return moment.tz(rawDate, this.timezone).fromNow();
        },
        updateSelectedList(documentTasks, action) {
            let newList = {...this.selectedList}
            if (action === "add") {
                newList[documentTasks.pk] = documentTasks
            } else {
                delete newList[documentTasks.pk]
            }
            this.selectedList = {...newList}
        },
        loadPrev() {
            this.currentPage -= 1;
            this.getDocumentTasks();
        },
        loadNext() {
            this.currentPage += 1;
            this.getDocumentTasks();
        },
        onSort({ field, direction }) {
            this.sortState = { value: field, direction };
            this.currentPage = 1;
            this.getDocumentTasks();
        },
        onSelectAll() {
            const selectable = this.results.filter((item) => this.hasActiveTasks(item));
            const allSelected = selectable.length > 0 && selectable.every((item) => this.selectedList[item.pk]);
            selectable.forEach((item) => {
                this.updateSelectedList(item, allSelected ? "remove" : "add");
            });
        },
        onToggleSelected(_event, pk) {
            const item = this.results.find((i) => i.pk === pk);
            if (!item || !this.hasActiveTasks(item)) return;
            this.updateSelectedList(item, this.selectedList[item.pk] ? "remove" : "add");
        },
        async getDocumentTasks() {
            let params = {
                page: this.currentPage,
            }

            if (this.selectedState !== "") params["task_state"] = this.selectedState
            if (this.selectedUser !== "") params["user_id"] = this.selectedUser
            if (this.documentName !== "") params["name"] = this.documentName
            if (this.sortState.direction !== 0) {
                const prefix = this.sortState.direction === -1 ? "-" : "";
                const field = this.sortState.value === "owner" ? "owner__username" : this.sortState.value;
                params["ordering"] = prefix + field;
            }

            await this.$store.dispatch("fetchDocumentsTasks", params);
        },
    },
};
</script>

<style scoped>
.docstasks-list ::v-deep .escr-select-all,
.docstasks-list ::v-deep .escr-select-column {
    width: 56px;
}
</style>
