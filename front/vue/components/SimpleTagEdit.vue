<template>
    <!--<a href="#"
        v-bind:id="iddoc"
        v-on:click="launchmodal"
        title="Manage tags"
        class="btn btn-info btn-sm set-tag-meta btn-primary"
        data-toggle="modal"
        data-target="#tagsModal">-->
        <i @click="launchmodal" class="btn btn-info btn-sm fas fa fa-tags" data-toggle="modal" data-target="#tagsModal" ref="tagedit"></i>
    <!--</a>
    <button  
            type="button" 
            value="" 
            v-on:click="launchmodal"  
            class="btn btn-primary set-tag-meta" 
            title="Manage tags"
            data-toggle="modal"
            data-target="#tagsModal"
            data-id=>
                <i v-bind:id="iddoc" class="fas fa fa-tags"></i>
    </button>-->
</template>

<script>

export default {
    props: [
        'documentId',
    ],
    // data () {
    //     return {
    //         docid: 0
    //     }
    // },
    // computed: {
    //     iddoc() {
    //         return this.docid;
    //     },
    // },
    // /*created(){
    //     this.docid = this.documentId;
    // },*/
    // beforeCreate() {
    //     this.$nextTick(function () {
    //         this.docid = this.documentId;
    //     })
    // },
    methods: {
        async launchmodal(event){
            let document_id = event.target.getAttribute('document_id');
            console.log('tagedit');
            console.log($(this.$refs.tagedit).attr('document_id'));
            this.$store.commit('documentslist/setDocumentID', document_id);
            await this.$store.dispatch('documentslist/getunlinktagbydocument', document_id);
        },
    }
}
</script>

<style scoped>
</style>
