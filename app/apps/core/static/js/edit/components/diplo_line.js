var diploLine = LineBase.extend({
    methods: {
        setEdit(ev) {
            this.editing = ev.target;
        },
        editableContent(ev) {
            if (this.editing && ev.target == this.editing)
                this.editing.setAttribute('contenteditable', true);
            // ev.target.focus();
        },
        editNext(ev) {
            ev.preventDefault();
            // TODO
            // ev.target.parent. nextchild.focus;
        }
    }
});
