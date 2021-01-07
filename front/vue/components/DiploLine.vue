<template>
</template>

<script>
import LineBase from './LineBase.vue';

export default LineBase.extend({
    props: ['line', 'ratio'],
    computed: {
        showregion() {
            let idx = this.$parent.part.lines.indexOf(this.line);
            if (idx) {
                let pr = this.$parent.part.lines[idx - 1].region;
                if (this.line.region == pr)
                    return "";
                else
                    return this.getRegion() + 1 ;
            } else {
                return this.getRegion() + 1 ;
            }
        }
    },
    mounted() {
        Vue.nextTick(function() {
            this.$parent.appendLine();
            if (this.line.currentTrans) this.setElContent(this.line.currentTrans.content);
        }.bind(this));
    },
    beforeDestroy() {
        let el = this.getEl();
        if (el != null) {
            el.remove();
        }
    },
    watch: {
        'line.order': function(n, o) {
            // make sure it's at the right place,
            // in case it was just created or the ordering got recalculated
            let index = Array.from(this.$el.parentNode.children).indexOf(this.$el);
            if (index != this.line.order) {
                this.$el.parentNode.insertBefore(
                    this.$el,
                    this.$el.parentNode.children[this.line.order]);
                this.setElContent(this.line.currentTrans.content);
            }
        },
        'line.currentTrans': function(n, o) {
            if (n!=undefined) {
                this.setElContent(n.content);
            }
        }
    },
    methods: {
        getEl() {
            return this.$parent.editor.querySelector('div:nth-child('+parseInt(this.line.order+1)+')');
        },
        setElContent(content) {
            let line = this.getEl();
            if (line) line.textContent = content;
        },
        getRegion() {
            return this.$parent.part.regions.findIndex(r => r.pk == this.line.region);
        }
    }
});
</script>

<style scoped>
</style>