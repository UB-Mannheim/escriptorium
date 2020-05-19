const BasePanel = Vue.extend({
    props: ['part'],
    data() {
        return {
            ratio: 1
        };
    },
    updated() {
        this.refresh();
    },
    methods: {
        setRatio() {
            this.ratio = this.$el.firstChild.clientWidth / this.part.image.size[0];
        },
        refresh() {
            Vue.nextTick(function() {
                this.setRatio();
                this.updateView();
            }.bind(this));
        },
        updateView() {}
    }
});
