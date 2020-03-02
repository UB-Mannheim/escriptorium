var LineBase = Vue.extend({
    props: ['line', 'ratio'],
    methods: {
        showOverlay() {
            if (this.line && this.line.mask) {
                Array.from(document.querySelectorAll('.panel-overlay')).map(
                    function(e) {
                        // TODO: transition
                        e.style.display = 'block';
                        e.querySelector('polygon').setAttribute('points', this.maskPoints);
                    }.bind(this)
                );
            }
        },
        hideOverlay() {
            Array.from(document.querySelectorAll('.panel-overlay')).map(
                function(e) {
                    e.style.display = 'none';
                }
            );
        },
    },
    computed: {
        transcriptionContent: {
            // TODO: doesnt work
            get() {
            if (!this.line || !this.line.transcription) return '';
                return this.line.transcription.content;
            },
            set(newValue) {
                this.line.transcription.content = newValue;
                // is this ok ?
                this.$parent.$parent.$emit('update:transcription', this.line.transcription);
            }
        },
        maskPoints() {
            if (this.line == null || this.line.mask === null) return '';
            return this.line.mask.map(pt => Math.round(pt[0]*this.ratio)+','+Math.round(pt[1]*this.ratio)).join(' ');
        },
        baselinePoints() {
            var baseline, ratio = this.ratio;
            function ptToStr(pt) {
                return Math.round(pt[0]*ratio)+' '+Math.round(pt[1]*ratio);
            }
            if (this.line == null || this.line.baseline === null) {
                baseline = this.fakeBaseline;
            } else {
                baseline = this.line.baseline;
            }
            return 'M '+baseline.map(pt => ptToStr(pt)).join(' L ');
        }
    }
});
