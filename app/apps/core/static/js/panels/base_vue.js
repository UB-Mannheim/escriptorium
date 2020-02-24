var BasePanel = Vue.extend({
    props: ['part'],
    data() {
        return {ratio: 1};
    },
    updated() {
        this.refresh();
    },
    computed: {
        imageSrc() {
            return (this.part !== null
                    && (this.part.image.thumbnails.large
                        || this.part.image.uri));
        }
    },
    methods: {
        getRatio() {
            return this.ratio;
        },
        setRatio() {
            this.ratio = this.$el.scrollWidth / this.part.image.size[0];
        },
        refresh() {
            this.setRatio();
            this.updateView();
        },
        updateView() {}
    }
});
