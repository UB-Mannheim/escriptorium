<template>
    <div class="m-auto">
        <div
            v-if="$store.state.parts.loaded"
            class="nav-div nav-item form-inline"
        >
            <select
                id="document-transcriptions"
                v-model="$store.state.transcriptions.selectedTranscription"
                title="Transcription"
                class="form-control custom-select"
            >
                <option
                    v-for="transcription in $store.state.transcriptions.all"
                    v-if="transcription.archived == false"
                    :key="transcription.pk"
                    :value="transcription.pk"
                >
                    {{ transcription.name|truncate(48, "...") }}
                </option>
            </select>
            <button
                type="button"
                class="btn btn-primary fas fa-cog ml-1"
                title="Transcription management"
                data-toggle="modal"
                data-target="#transcriptionsManagement"
            />
            <div
                id="transcriptionsManagement"
                class="modal ui-draggable"
                tabindex="-1"
                role="dialog"
            >
                <div
                    class="modal-dialog"
                    role="document"
                >
                    <div class="modal-content">
                        <div class="modal-header ui-draggable-handle">
                            <h5 class="modal-title">
                                Transcriptions management
                            </h5>
                            <button
                                type="button"
                                class="close"
                                data-dismiss="modal"
                                aria-label="Close"
                            >
                                <span aria-hidden="true">&times;</span>
                            </button>
                        </div>
                        <div class="modal-body">
                            <div>
                                <span>Compare</span>
                                <span class="float-right">Delete</span>
                            </div>
                            <div
                                v-for="trans in $store.state.transcriptions.all"
                                v-if="trans.archived == false"
                                v-bind="trans"
                                :key="trans.pk"
                                class="inline-form form-check mt-1"
                            >
                                <input
                                    :id="'opt' + trans.pk"
                                    v-model="$store.state.transcriptions.comparedTranscriptions"
                                    type="checkbox"
                                    class="form-check-input"
                                    :value="trans.pk"
                                >
                                <label
                                    :for="'opt'+trans.pk"
                                    class="form-check-label col transcription-name"
                                >{{ trans.name }}</label>
                                <button
                                    v-if="trans.name!='manual' && trans.pk != $store.state.transcriptions.selectedTranscription"
                                    :data-trPk="trans.pk"
                                    class="btn btn-danger fas fa-trash"
                                    title="Completely remove the transcription and all of its content!&#10;You can not remove the manual or the current transcription."
                                    @click="deleteTranscription"
                                />
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
export default {
    filters: {
        truncate: function (text, length, suffix) {
            if (text.length > length) {
                return text.substring(0, length) + suffix;
            } else {
                return text;
            }
        },
    },
    methods: {
        async deleteTranscription(ev) {
            let transcription = ev.target.dataset.trpk;
            // I lied, it's only archived
            if(confirm("Are you sure you want to delete the transcription? This will affect ALL pages of the document!")) {
                this.$store.dispatch("transcriptions/archive", transcription)
                    .then((test) => {
                        ev.target.parentNode.remove();
                        this.$store.commit("transcriptions/removeComparedTranscription", parseInt(transcription));
                    })
                    .catch((err) => {
                        console.log("couldn't archive transcription #", transcription, err)
                    })
            }
        },
    }
}
</script>

<style scoped>
</style>
