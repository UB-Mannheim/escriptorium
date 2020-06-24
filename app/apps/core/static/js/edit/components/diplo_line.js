var diploLine = LineBase.extend({
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
    watch: {
        'line.order': function(o, n) {
            // make sure it's at the right place,
            // in case it was just created or the ordering got recalculated
            let index = Array.from(this.$el.parentNode.children).indexOf(this.$el);
            if (index != this.line.order) {
                this.$el.parentNode.insertBefore(
                    this.$el,
                    this.$el.parentNode.children[this.line.order]);
            }
        }
    },
    methods: {
        startEdit(ev){
            // if we are selecting text we don't want to start editing
            // to be able to do multiline selection
            if (document.getSelection().toString()) {
                return true;
            }
            this.$parent.setEditLine(this.line);
            this.$parent.$parent.blockShortcuts = true;
        },
        stopEdit(ev) {
            this.$parent.$parent.blockShortcuts = false;
        },

        setContent(content){
            let id = this.line.pk;
            $("#" + id).text(content);
            this.line.currentTrans.content = content;
        },
        onPaste(e){
            let pastedData = e.clipboardData.getData('text/plain');
            let pasted_data_split = pastedData.split('\n');

            if (pasted_data_split.length < 2) {
                return
            } else {
                e.preventDefault();

                if (pasted_data_split[pasted_data_split.length - 1] == "")
                    pasted_data_split.pop();

                let index = this.$parent.$children.indexOf(this);

                for (let i = 1; i < pasted_data_split.length; i++) {
                    if (this.$parent.$children[index + i]) {
                        let content = pasted_data_split[i];
                        let child = this.$parent.$children[index + i];
                        child.setContent(content);
                        child.addToList();
                    } else {
                        let content = pasted_data_split.slice(i - 1).join('\n');
                        let child = this.$parent.$children[index + 1];
                        child.setContent(content);
                    }
                }
                this.$parent.toggleSave();
            }
        },
        getRegion(){
            return this.$parent.part.regions.findIndex(r => r.pk == this.line.region);
        }
    }
});
