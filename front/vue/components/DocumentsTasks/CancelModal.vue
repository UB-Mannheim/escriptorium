<template>
    <div
        :id="id"
        ref="cancelTasksModal"
        class="modal fade"
        tabindex="-1"
        role="dialog"
        aria-hidden="true"
    >
        <div
            class="modal-dialog modal-dialog-centered modal-md"
            role="document"
        >
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" v-translate>
                        Cancel tasks
                    </h5>
                    <button
                        type="button"
                        class="close"
                        data-dismiss="modal"
                        aria-label="Close"
                        :disabled="loading"
                    >
                        <span aria-hidden="true">&times;</span>
                    </button>
                </div>
                <div class="modal-body">
                    <p v-translate>You're about to cancel all pending/running tasks for documents:</p>
                    <ul>
                        <li
                            v-for="document in documentsTasks"
                            :key="document.pk"
                        >
                            <strong>{{ document.name }}</strong> <span v-translate>owned by</span> <strong>{{ document.owner }}</strong>
                        </li>
                    </ul>
                    <p v-translate>Please confirm that you want to proceed.</p>
                </div>
                <div class="modal-footer">
                    <button
                        type="button"
                        class="btn btn-secondary"
                        data-dismiss="modal"
                        :disabled="loading"
                        v-translate
                    >
                        Abort
                    </button>
                    <button
                        type="button"
                        class="btn btn-danger"
                        :disabled="loading"
                        @click="cancelTasks()"
                    >
                        {{ loading ? $gettext("Canceling tasks...") : $gettext("Cancel tasks") }}
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
export default {
    props: [
        "id",
        "documentsTasks",
    ],
    data() {
        return {
            loading: false,
        }
    },
    methods: {
        async cancelTasks() {
            this.loading = true
            const successes = []
            const errors = []

            for (const document of this.documentsTasks) {
                try {
                    const data = await this.$store.dispatch("cancelDocumentTasks", document.pk)
                    successes.push(data.details)
                } catch (err) {
                    errors.push(err.response && err.response.data && err.response.data.error || err.message)
                }
            }

            this.$emit("cancel-success", successes)
            this.$emit("cancel-error", errors)
            this.loading = false
            $(this.$refs.cancelTasksModal).modal("hide")
        },
    }
}
</script>

<style scoped>
</style>
