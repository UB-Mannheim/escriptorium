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
          console.log("on past",pasted_data_split);

          if(pasted_data_split.length < 2){
                return
          }
          else {
            e.preventDefault();
            document.execCommand('inserttext', false, pasted_data_split[0]);

            if(pasted_data_split[pasted_data_split.length -1] =="")
                pasted_data_split.pop();
            let index = $(this).parent().index();
            let lines = $(".line-content");
            for (let i=index+1; i<index + pasted_data_split.length; i++){
                let value = pasted_data_split[i- index];
                $(lines[i]).text(value);
                // self.editAndSave(lines[i]);
                }
            }
        }
    }
});
