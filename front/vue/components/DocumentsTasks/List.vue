<template>
    <div>
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

        <table class="table table-hover">
            <tr>
                <th>
                    <input
                        v-model="selectAll"
                        class="ml-0"
                        type="checkbox"
                    >
                </th>
                <th>Name</th>
                <th>User</th>
                <th>Statistics</th>
                <th>Last task started</th>
                <th>Actions</th>
            </tr>
            <template v-if="$store.state.documentsTasks && $store.state.documentsTasks.results && $store.state.documentsTasks.results.length">
                <Row
                    v-for="documentTasks in $store.state.documentsTasks.results"
                    :key="documentTasks.pk"
                    :timezone="timezone"
                    :document-tasks="documentTasks"
                    :select-all="selectAll"
                    @cancel-success="cancelSucceeded"
                    @cancel-error="cancelFailed"
                    @selected="updateSelectedList"
                />
            </template>
            <template v-else>
                <tr>
                    <td colspan="6">
                        No document tasks to display.
                    </td>
                </tr>
            </template>
        </table>

        <ul class="pagination justify-content-end">
            <li class="page-item">
                <template v-if="$store.state.documentsTasks && $store.state.documentsTasks.previous">
                    <a
                        class="page-link"
                        @click="loadPrev()"
                    ><span aria-hidden="true">&lsaquo;</span></a>
                </template>
            </li>
            <li class="page-item">
                <template v-if="$store.state.documentsTasks && $store.state.documentsTasks.next">
                    <a
                        class="page-link"
                        @click="loadNext()"
                    ><span aria-hidden="true">&rsaquo;</span></a>
                </template>
            </li>
        </ul>

        <button
            data-toggle="modal"
            data-target="#cancelTasksModal"
            title="Cancel pending/running tasks for the selected documents"
            class="btn btn-danger"
            :disabled="!selectedList || !Object.values(selectedList).length"
        >
            Cancel all selected
        </button>

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
import Row from "./Row.vue";

export default {
    components: {
        CancelModal,
        Row,
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
            selectAll: false,
            selectedList: {},
        }
    },
    computed: {
        sortedUsersEntries () {
            return Object.entries(this.users).sort(([, a], [, b]) => {
                a = a.toLowerCase();
                b = b.toLowerCase();
                if (a < b) return -1;
                if (a > b) return 1;
                return 0;
            })
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
        async getDocumentTasks() {
            let params = {
                page: this.currentPage,
            }

            if (this.selectedState !== "") params["task_state"] = this.selectedState
            if (this.selectedUser !== "") params["user_id"] = this.selectedUser
            if (this.documentName !== "") params["name"] = this.documentName

            await this.$store.dispatch("fetchDocumentsTasks", params);
        },
    },
};
</script>

<style scoped>
</style>
