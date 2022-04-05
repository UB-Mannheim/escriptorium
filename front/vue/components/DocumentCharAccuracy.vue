<template>
    <div class="d-inline-flex">
        <div v-bind:value="charAccuracy" v-if="charAccuracy > 0">
            <span class="badge m-1" v-bind:title="model">{{ `${(charAccuracy * 100).toFixed(2)}%` }}</span>
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
            charAccuracy: 0,
            model: "",
        }
    },
    mounted(){
        this.initFetch();
    },
    computed: {
        charAccuracyList() {
            return this.$store.state.documentslist.charAccuracyListPerDocument;
        },
    },
    methods: {
        initFetch(){
            this.$store.commit('documentslist/setProjectID', this.projectId);
            this.$store.dispatch('documentslist/fetchCharAccuracy');  
        },
        refreshAccuracy() {
            const { accuracy, model } = this.charAccuracyList.find(doc => doc.pk === this.documentId);
            this.charAccuracy = accuracy;
            this.model = model;
        }
    },
    watch: {
        "$store.state.documentslist.charAccuracyListPerDocument": {
            handler: function() {
                this.refreshAccuracy();
            },
            immediate: false,
            deep: true
        },
    }
}
</script>
