<template />

<script>
export default Vue.extend({
    props: ["region"],
    data() { return {
        segmenterObject: null,
    };},
    watch: {
        "region.loaded": {
            immediate: true,
            handler: function (n) {
                if (n) this.load();
            }
        }
    },
    methods: {
        load() {
            this.segmenter = this.$parent.segmenter;
            let segmenterObject = this.segmenter.regions.find((l)=>l.context.pk==this.region.pk)
            if (segmenterObject === undefined) {
                this.segmenterObject = this.segmenter.loadRegion(this.region);
            } else {
                this.segmenterObject = segmenterObject;
            }
        }
    }
});
</script>

<style scoped>
</style>
