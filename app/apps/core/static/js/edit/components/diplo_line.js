var diploLine = LineBase.extend({
    props: ['line', 'ratio'],
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
        transcriptionContent(){
            return ""
        },
    }
});
