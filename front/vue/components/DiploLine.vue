<template />

<script>
import { LineBase } from "../../src/editor/mixins.js";

export default Vue.extend({
    mixins: [LineBase],
    computed: {
        showregion() {
            let idx = this.$store.state.lines.all.indexOf(this.line);
            if (idx) {
                let pr = this.$store.state.lines.all[idx - 1].region;
                if (this.line.region == pr)
                    return "";
                else
                    return this.getRegion() + 1 ;
            } else {
                return this.getRegion() + 1 ;
            }
        }
    },
    watch: {
        "line.order": function(n, o) {
            // make sure it's at the right place,
            // in case it was just created or the ordering got recalculated
            this.$el.parentNode.insertBefore(
                this.$el,
                this.$el.parentNode.children[this.line.order]);
            this.setElContent(this.line.currentTrans.content);
        },
        "line.currentTrans": function(n, o) {
            if (n!=undefined) {
                this.setElContent(n.content);
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
    methods: {
        getEl() {
            return this.$parent.$refs.diplomaticLines.querySelector("div:nth-child("+parseInt(this.line.order+1)+")");
        },
        setElContent(content) {
            let line = this.getEl();
            if (line) line.textContent = content;
        },
        getRegion() {
            return this.$store.state.regions.all.findIndex((r) => r.pk == this.line.region);
        }
    }
});
</script>

<style scoped>
</style>
