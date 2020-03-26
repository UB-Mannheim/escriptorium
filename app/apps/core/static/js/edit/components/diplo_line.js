var diploLine = LineBase.extend({
    props: ['line', 'ratio'],
    methods: {
        setEdit(ev) {
            this.editing = ev.target;
            console.log("call setEdit");

        },
        editableContent(ev) {
            if (this.editing && ev.target == this.editing)
                this.editing.setAttribute('contenteditable', true);
            ev.target.focus();
            console.log("call editableContent");
        },
        transcriptionContent(){
            return ""
        },
    }
});
