const BasePanel = Vue.extend({
    props: ['part'],
    data() {
        return {
            ratio: 1
        };
    },
    watch: {
        'part.loaded': function(n, o) {
            if (n && !o) this.refresh();
        }
    },
    methods: {
        setRatio() {
            this.ratio = this.$el.firstChild.clientWidth / this.part.image.size[0];
        },
        refresh() {
            if (this.part.loaded) {
                Vue.nextTick(function() {
                    this.setRatio();
                    this.updateView();
                }.bind(this));
            }
        },
        updateView() {}
    }
});
