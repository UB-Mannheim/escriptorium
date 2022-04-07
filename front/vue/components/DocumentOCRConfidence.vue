<template>
    <div class="d-inline-flex">
        <div v-bind:value="ocrConfidence" v-if="ocrConfidence > 0">
            <span class="badge m-1" v-bind:title="model">{{ `${(ocrConfidence * 100).toFixed(2)}%` }}</span>
        </div>
    </div>
</template>


<script>

export default {
    props: [
        'projectId',
        'documentId',
    ],
    data () {
        return {
            ocrConfidence: 0,
            model: "",
        }
    },
    mounted(){
        this.initFetch();
    },
    computed: {
        ocrConfidenceList() {
            return this.$store.state.documentslist.ocrConfidenceListPerDocument;
        },
    },
    methods: {
        initFetch(){
            this.$store.commit('documentslist/setProjectID', this.projectId);
            this.$store.dispatch('documentslist/fetchOCRConfidence');  
        },
        refreshConfidence() {
            const { confidence, model } = this.ocrConfidenceList.find(doc => doc.pk === this.documentId);
            this.ocrConfidence = confidence;
            this.model = model;
        }
    },
    watch: {
        "$store.state.documentslist.ocrConfidenceListPerDocument": {
            handler: function() {
                this.refreshConfidence();
            },
            immediate: false,
            deep: true
        },
    }
}
</script>
