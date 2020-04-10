const BasePanel = Vue.extend({
    props: ['part', 'full-size-image'],
    data() {
      return {ratio: 1};
    },
    updated() {
        this.refresh();
    },
    computed: {
        imageSrc() {
            let src = (this.part.loaded
                    && (!this.fullSizeImage
                     && this.part.image.thumbnails.large
                     || this.part.image.uri));
            return src;
        },
    },
    methods: {
        setRatio() {
            this.ratio = this.$el.firstChild.clientWidth / this.part.image.size[0];
        },
        refresh() {
            if (this.part.loaded) {
                this.setRatio();
                this.updateView();
            }
        },
        updateView() {}
    }
});
