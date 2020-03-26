var DiploPanel = BasePanel.extend({

    data() { return {
        editLine: null,
        save: false, //show save button
    };},
    components: {
        'diploline': diploLine,
    },
    methods:{
        togglePanel(){},
        saveContent(){
            console.log("call saveContent");
        },
        toggleSave(){
            let timer = 0;
            clearTimeout(timer);
            timer = setTimeout(function (){
            if(this.save){
               this.saveContent();
            }
            this.save = !this.save;
        }.bind(this), 1000);
        },
        editNext(ev) {
            ev.preventDefault();
            index = this.part.lines.indexOf(this.editLine);
            if(index < this.part.lines.length - 1) {
                this.editLine = this.part.lines[index + 1];
                let next = this.$children[index +1].$el.firstElementChild.lastChild;
                let elt = $("#"+this.editLine.pk);
                console.log("elt",elt);
                elt.focus();
            }
        },
        setEditLine(l) {
            this.editLine = l;
        }
    },

});
