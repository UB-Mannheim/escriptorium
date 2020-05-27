const segRegion = Vue.extend({
    props: ['region'],
    data() { return {
        segmenterObject: null,
    };},
    mounted() {
        this.segmenter = this.$parent.segmenter;
        let segmenterObject = this.segmenter.regions.find(l=>l.context.pk==this.region.pk)
        if (segmenterObject === undefined) {
            this.segmenterObject = this.segmenter.loadRegion(this.region);
        } else {
            this.segmenterObject = segmenterObject;
        }
    }
});

const segLine = Vue.extend({
    props: ['line'],
    data() { return {
        segmenterObject: null,
    };},
    mounted() {
        this.segmenter = this.$parent.segmenter;
        let segmenterObject = this.segmenter.lines.find(l=>l.context.pk==this.line.pk)
        if (segmenterObject === undefined) {
            let region = this.line.region && this.segmenter.regions.find(l=>l.context.pk==this.line.region) || null;
            this.segmenterObject = this.segmenter.loadLine(this.line, region);
        } else {
            // drawn in the editor
            this.segmenterObject = segmenterObject;
        }
    },
    watch: {
        'line.mask': function(n, o) {
            if (!_.isEqual(n, o)) {
                this.segmenterObject.update(undefined, n);
            }
        },
        'line.region': function(n, o) {
            if (n != o) {
                let region = this.line.region && this.segmenter.regions.find(l=>l.context.pk==this.line.region) || null;
                // Note this function's api is kinda weird
                this.segmenterObject.update(undefined, undefined, region);
            }
        },
        'line.order': function(n, o) {
            if (n != o) {
                // Note this function's api is kinda weird
                this.segmenterObject.update(undefined, undefined, undefined, n);
            }
        },
    }
});
