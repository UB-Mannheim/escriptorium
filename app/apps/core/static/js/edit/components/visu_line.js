const visuLine = Vue.extend({
    props: ['line', 'ratio'],
    watch: {
        'line.currentTrans.content': function(n, o) {
            this.$nextTick(this.reset);
        },
        'line.baseline': function(n, o) {
            this.$nextTick(this.reset);
        }
    },
    methods: {
        computeLineHeight() {
            let lineHeight;
            if (this.line.mask) {
                let poly = this.line.mask.flat(1).map(pt => Math.round(pt));
                var area = 0;
                // A = 1/2(x_1y_2-x_2y_1+x_2y_3-x_3y_2+...+x_(n-1)y_n-x_ny_(n-1)+x_ny_1-x_1y_n),
                for (let i=0; i<poly.length; i++) {
                    let j = (i+1) % poly.length; // loop back to 1
                    area += poly[i][0]*poly[j][1] - poly[j][0]*poly[i][1];
                }
                area = Math.abs(area*this.ratio);
                lineHeight = area / this.pathElement.getTotalLength();
            } else {
                lineHeight = 30;
            }

            lineHeight = Math.max(Math.min(Math.round(lineHeight), 100), 5);
            this.textElement.style.fontSize =  lineHeight * (1/2) + 'px';
        },
        computeTextLength() {
            if (!this.line.currentTrans) return;
            content = this.line.currentTrans.content;
            if (content) {
                // adjust the text length to fit in the box
                let textLength = this.textElement.getComputedTextLength();
                let pathLength = this.pathElement.getTotalLength();
                if (textLength && pathLength) {
                    this.textElement.setAttribute('textLength', pathLength+'px');
                }
            }
        },
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
        edit() {
            this.$parent.editLine = this.line;
        },
        reset() {
            this.computeLineHeight();
            this.computeTextLength();
        },
    },
    computed: {
        polyElement() { return this.$el.querySelector('polygon'); },
        pathElement() { return this.$el.querySelector('path'); },
        textElement() { return this.$el.querySelector('text'); },
        textPathId() {
            return this.line ? 'textPath'+this.line.pk : '';
        },
        maskStrokeColor() {
            if (this.line.currentTrans && this.line.currentTrans.content) {
                return 'none';
            } else {
                return 'lightgrey';
            }
        },
        maskPoints() {
            if (this.line == null || !this.line.mask) return '';
            return this.line.mask.map(pt => Math.round(pt[0]*this.ratio)+','+Math.round(pt[1]*this.ratio)).join(' ');
        },
        fakeBaseline() {
            // create a fake path based on the mask,
            var min = this.line.mask.reduce((minPt, curPt) => (curPt[0] < minPt[0]) ? curPt : minPt);
            var max = this.line.mask.reduce((maxPt, curPt) => (curPt[0] > maxPt[0]) ? curPt : maxPt);
            return [min, max];
        },
        pathStrokeColor() {
            if (this.line.currentTrans && this.line.currentTrans.content) {
                return 'none';
            } else {
                return 'blue';
            }
        },
        baselinePoints() {
            var baseline, ratio = this.ratio;
            function ptToStr(pt) {
                return Math.round(pt[0]*ratio)+' '+Math.round(pt[1]*ratio);
            }
            if (this.line == null || this.line.baseline === null) {
                baseline = this.fakeBaseline;
            } else {
                baseline = this.line.baseline
            }
            return 'M '+baseline.map(pt => ptToStr(pt)).join(' L ');
        },
    }
});
