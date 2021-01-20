<template>
</template>

<script>
window.Vue = require('vue/dist/vue');

export default Vue.extend({
    data() {
        return {
            ratio: 1
        };
    },
    watch: {
        '$store.state.parts.loaded': function(n, o) {
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
});
</script>

<style scoped>
</style>