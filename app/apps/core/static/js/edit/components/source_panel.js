const SourcePanel = BasePanel.extend({
    props: ['part', 'fullsizeimage'],
    computed: {
        imageSrc() {
            let src = !this.fullsizeimage
                   && this.part.image.thumbnails.large
                   || this.part.image.uri;
            return src;
        }
    },
    mounted: function() {
        this.$parent.zoom.register(
            this.$el.querySelector('#source-zoom-container'),
            {map: true});
    }
});
