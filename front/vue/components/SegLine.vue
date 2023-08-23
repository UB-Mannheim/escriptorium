<template />

<script>
export default Vue.extend({
    props: ["line"],
    data() { return {
        segmenterObject: null,
    };},
    watch: {
        "line.loaded": {
            immediate: true,
            handler: function (n) {
                if (n) this.load();
            }
        },
        "line.mask": function(n, o) {
            if (!_.isEqual(n, o)) {
                this.segmenterObject.update(undefined, n);
            }
        },
        "line.region": function(n, o) {
            if (n != o) {
                let region = this.line.region && this.segmenter.regions.find((l)=>l.context.pk==this.line.region) || null;
                // Note this function's api is kinda weird
                this.segmenterObject.update(undefined, undefined, region);
            }
        },
        "line.order": function(n, o) {
            if (n != o) {
                // Note this function's api is kinda weird
                this.segmenterObject.update(undefined, undefined, undefined, n);
            }
        },
    },
    methods: {
        load() {
            this.segmenter = this.$parent.segmenter;
            let segmenterObject = this.segmenter.lines.find((l)=>l.context.pk==this.line.pk)
            if (segmenterObject === undefined) {
                let region = this.line.region && this.segmenter.regions.find((l)=>l.context.pk==this.line.region) || null;
                this.segmenterObject = this.segmenter.loadLine(this.line, region);
            } else {
                // drawn in the editor
                this.segmenterObject = segmenterObject;
            }
        }
    }
});
</script>

<style scoped>
</style>
