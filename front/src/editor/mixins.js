window.Vue = require('vue/dist/vue');

export var BasePanel = {
    data() {
        return {
            ratio: 1
        };
    },
    created() {
        // Update ratio on window resize
        window.addEventListener("resize", this.refresh);
    },
    destroyed() {
        window.removeEventListener("resize", this.refresh);
    },
    watch: {
        '$store.state.parts.loaded': function(n, o) {
            if (n) {
                this.refresh();
            }
        },
        '$store.state.document.visible_panels': function(n, o) {
            if (this.$store.state.parts.loaded) {
                this.refresh();
            }
        }
    },
    methods: {
        setRatio() {
            this.ratio = this.$el.firstChild.clientWidth / this.$store.state.parts.image.size[0];
        },
        refresh() {
            this.setRatio();
            this.updateView();
        },
        updateView() {}
    }
}

export var LineBase = {
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
    computed : {
        maskPoints() {
            if (this.line == null || !this.line.mask) return '';
            return this.line.mask.map(pt => Math.round(pt[0]*this.ratio)+','+Math.round(pt[1]*this.ratio)).join(' ');
        },
    }
}
