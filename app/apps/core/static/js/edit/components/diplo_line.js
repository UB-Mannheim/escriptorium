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
                this.setContent(this.$refs.content[0].innerHTML);
                if(this.line.transcription.pk){
                    this.$parent.$emit('update:transcription:content', this.line.transcription);

                }
                else {
                 this.$parent.$emit('create:transcription', this.line.transcription);
                }
                 this.$parent.toggleSave();
            }.bind(this), 1000);

        },
        pushNewVersion(){

        },
        setContent(content){
                this.line.transcription.content = content;
                moment.tz(this.line.transcription.version_updated_at, this.timeZone);

        }
    }
});
