var diploLine = LineBase.extend({
    props: ['line', 'ratio'],
    created() {
        // this.timeZone = moment.tz.guess();
        Vue.nextTick(function() {
            this.$content = this.$refs.content[0];
        }.bind(this));
    },
    computed: {
            region() {
                let idx = this.$parent.part.lines.indexOf(this.line);
                if (idx) {
                    let pr = this.$parent.part.lines[idx - 1].region;
                    if (this.line.region == pr)
                        return "";
                    else
                        return this.line.region
                }
                else {
                    return this.line.region
                }
            }
    },
    methods: {
        startEdit(ev) {
            this.$content.setAttribute('contenteditable', true);
            this.$content.focus();
            this.$parent.setEditLine(this.line);
            this.$content.style.backgroundColor =  '#F8F8F8';
        },
        stopEdit(ev) {
            this.$content.style.backgroundColor = 'white';
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
                document.execCommand('inserttext', false, pasted_data_split[0]);

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
