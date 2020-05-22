var diploLine = LineBase.extend({
    props: ['line', 'ratio'],
    created() {
        Vue.nextTick(function() {
            this.$content = this.$refs.content[0];
        }.bind(this));
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
        startEdit(ev) {
            // if we are selecting text we don't want to start editing
            // to be able to do multiline selection
            if (document.getSelection().toString()) {
                return true;
            }
            this.$content.setAttribute('contenteditable', true);
            this.$content.focus();  // needed in case we edit from the panel
            this.$parent.setEditLine(this.line);
            this.$content.style.backgroundColor =  '#F8F8F8';
            this.$parent.$parent.blockShortcuts = true;
        },
        stopEdit(ev) {
            this.$content.setAttribute('contenteditable', false);
            this.$content.style.backgroundColor = 'white';
            this.$parent.$parent.blockShortcuts = false;
            this.pushUpdate();
        },
        pushUpdate(){
            // set content of input to line content
            if (this.line.transcription.content != this.$content.textContent) {
                this.line.transcription.content = this.$content.textContent;
                this.addToList();
                // call save of parent method
                this.$parent.toggleSave();
            }
        },
        setContent(content){
            let id = this.line.pk;
            $("#" + id).text(content);
            this.line.transcription.content = content;
        },
        onPaste(e) {
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
                        child.addToList();
                    }
                }
            }
        },
        addToList(){
            if(this.line.transcription.pk)
                this.$parent.$emit('update:transcription:content', this.line.transcription);
            else
                this.$parent.$emit('create:transcription', this.line.transcription);
        }
    }
});
