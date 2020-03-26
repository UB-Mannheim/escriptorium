var LineBase = Vue.extend({
    props: ['line', 'ratio'],
    methods: {
        setRatio() {
            this.ratio = this.$el.firstChild.clientWidth / this.part.image.size[0];
        },
        refresh() {
            this.setRatio();
            this.updateView();
        },
        updateView() {},
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
    computed : {
        maskPoints() {
            if (this.line == null || !this.line.mask) return '';
            return this.line.mask.map(pt => Math.round(pt[0]*this.ratio)+','+Math.round(pt[1]*this.ratio)).join(' ');
        },
    }
});
