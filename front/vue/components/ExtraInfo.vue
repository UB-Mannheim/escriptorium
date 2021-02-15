<template>
    <div>
        <div class="nav-div nav-item ml-2">
            <span v-if="$store.state.document.name" id="part-name">{{ $store.state.document.name }}</span>
            <span id="part-title" v-if="$store.state.parts.loaded">{{ $store.state.parts.title }} - {{ $store.state.parts.filename }} - ({{ imageSize }})</span>
            <span class="loading" v-if="!$store.state.parts.loaded">Loading&#8230;</span>
        </div>
        <div v-if="$store.state.parts.loaded" class="nav-div nav-item form-inline ml-auto mr-auto">
            <select v-model="$store.state.transcriptions.selectedTranscription"
                    id="document-transcriptions"
                    title="Transcription"
                    class="form-control custom-select">
                <option v-for="transcription in $store.state.transcriptions.all"
                        v-bind:key="transcription.pk"
                        v-bind:value="transcription.pk">{{ transcription.name }}</option>
            </select>
            <button type="button"
                    class="btn btn-primary fas fa-cog ml-1"
                    title="Transcription management"
                    data-toggle="modal"
                    data-target="#transcriptionsManagement"></button>
            <div id="transcriptionsManagement"
                class="modal ui-draggable"
                tabindex="-1"
                role="dialog">
                <div class="modal-dialog" role="document">
                    <div class="modal-content">
                        <div class="modal-header ui-draggable-handle">
                            <h5 class="modal-title">Transcriptions management</h5>
                            <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                                <span aria-hidden="true">&times;</span>
                            </button>
                        </div>
                        <div class="modal-body">
                            <div>
                                <span>Compare</span>
                                <span class="float-right">Delete</span>
                            </div>
                            <div v-for="trans in $store.state.transcriptions.all"
                                v-bind="trans"
                                v-bind:key="trans.pk"
                                class="inline-form form-check mt-1">
                                <input type="checkbox" class="form-check-input"
                                    v-bind:id="'opt' + trans.pk"
                                    v-model="$store.state.transcriptions.comparedTranscriptions"
                                    v-bind:value="trans.pk" />
                                <label v-bind:for="'opt'+trans.pk"
                                    class="form-check-label col">{{ trans.name }}</label>
                                <button v-bind:data-trPk="trans.pk"
                                        @click="deleteTranscription"
                                        class="btn btn-danger fas fa-trash"
                                        title="Completely remove the transcription and all of it's content!&#10;You can not remove the manual or the current transcription."></button>
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
    computed: {
        imageSize() {
            return this.$store.state.parts.image.size[0]+'x'+this.$store.state.parts.image.size[1];
        },
    },
    methods: {
        async deleteTranscription(ev) {
            let transcription = ev.target.dataset.trpk;
            // I lied, it's only archived
            if(confirm("Are you sure you want to delete the transcription?")) {
                await this.$store.dispatch('transcriptions/archive', transcription);
                ev.target.parentNode.remove();  // meh
                this.$store.commit('transcriptions/removeComparedTranscription', transcription);
            }
        },
    }
}
</script>

<style scoped>
</style>