var BasePanel = Vue.extend({
    props: ['part'],
    computed: {
        imageSrc: function() {
            return (this.part.image.thumbnails.large
                    || this.part.image.uri);
        }
    },
    methods: {
        getRatio: function() {
            return this.$parent.$el.clientWidth / 2 / this.part.image.size[0];
        }
    }
});