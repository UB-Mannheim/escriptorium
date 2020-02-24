var BasePanel = Vue.extend({
    props: ['part'],
    computed: {
        imageSrc() {
            return (this.part !== null
                    && (this.part.image.thumbnails.large
                        || this.part.image.uri));
        }
    },
    methods: {
        getRatio() {
            return this.$el.scrollWidth / this.part.image.size[0];
        }
    }
});
