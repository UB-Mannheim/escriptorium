let timer = 0;
var diploLine = LineBase.extend({
    props: ['line', 'ratio'],
    created() {
        this.timeZone = moment.tz.guess();
    },
    methods: {
        setEdit(ev) {
            this.editing = ev.target;

        },
        editableContent(ev) {
            if (this.editing && ev.target == this.editing)
                this.editing.setAttribute('contenteditable', true);
            ev.target.focus();
            this.$parent.setEditLine(this.line);
        },
        pushUpdate(){

            clearTimeout(timer);
            timer = setTimeout(function (){

                //set content of input to line content
                this.line.transcription.content = this.$refs.content[0].textContent;
                if(this.line.transcription.pk)
                    this.$parent.$emit('update:transcription:content', this.line.transcription);
                else
                 this.$parent.$emit('create:transcription', this.line.transcription);

                // call save of parent method
                 this.$parent.toggleSave();
            }.bind(this), 1000);

        },
        pushNewVersion(){

        },
        setContent(content){
                this.line.transcription.content = content;
                moment.tz(this.line.transcription.version_updated_at, this.timeZone);

        },
        onPast(e){
          let pastedData = e.clipboardData.getData('text/plain');
          let pasted_data_split = pastedData.split('\n');

          if(pasted_data_split.length < 2){
                return
          }
          else {
            e.preventDefault();
            document.execCommand('inserttext', false, pasted_data_split[0]);

            if(pasted_data_split[pasted_data_split.length -1] =="")
                pasted_data_split.pop();

            let index = this.$parent.$children.indexOf(this);
            for (let i=1; i<pasted_data_split.length; i++){

                 if(this.$parent.$children[index+i]) {
                     let content = pasted_data_split[i];
                     let child = this.$parent.$children[index+i];
                     let id = child.line.pk;
                     $("#"+id).text(content);
                }
                else {
                     let content = pasted_data_split.slice(i-1).join('\n');
                     let child = this.$parent.$children[index+1];
                     let id = child.line.pk;
                     $("#"+id).text(content);
                }

            }

            }
        }
    }
});
