var BasePanel = Vue.extend({
    props: ['part'],
    computed: {
        imageSrc() {
            return (this.part.image.thumbnails.large
                    || this.part.image.uri);
        }
    },
    methods: {
        getRatio() {
            let el = this.$el.firstChild;
            return el.clientWidth / this.part.image.size[0];
        }
    }
});
