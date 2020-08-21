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
        cleanSource(dirtyText) {
            // cleanup html and possibly other tags (?)
            var tmp = document.createElement("DIV");
            tmp.innerHTML = dirtyText;
            let clean = tmp.textContent || tmp.innerText || "";
            tmp.remove();
            return clean;
        },
        onPaste(e) {
            let pastedData = e.clipboardData.getData('text/plain');
            let pasted_data_split = pastedData.split('\n');

            if (pasted_data_split.length == 1) {
                // all of this just to call cleanSource on the data
                let paste = (event.clipboardData || window.clipboardData).getData('text');
                paste = this.cleanSource(paste);
                const selection = window.getSelection();
                if (!selection.rangeCount) return false;
                selection.deleteFromDocument();
                selection.getRangeAt(0).insertNode(document.createTextNode(paste));
            } else {
                //remove the last line if it's empty
                if (pasted_data_split[pasted_data_split.length - 1] == "") {
                    pasted_data_split.pop();
                }

                let index = this.$parent.$children.indexOf(this);
                for (let i = 0; i < pasted_data_split.length; i++) {
                    let content = pasted_data_split[i];
                    let child = this.$parent.$children[index + i];
                    if (child) {
                        child.$el.textContent = this.cleanSource(content);
                    }
                }
            }
            e.preventDefault();
        },
        getContentOrFake() {
            return this.line.currentTrans.content;
        },
        getRegion() {
            return this.$parent.part.regions.findIndex(r => r.pk == this.line.region);
        }
    }
});
