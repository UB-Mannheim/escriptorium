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
            $(ev.currentTarget).css('backgroundColor','white');

            let index = this.part.lines.indexOf(this.editLine);
            if(index < this.part.lines.length - 1) {
                this.setEditLine(this.part.lines[index + 1]);
                let st = $(".line-content").eq( $(".line-content").index( $(ev.currentTarget) ) + 1 );
                st.attr("contentEditable","true");
                st.css('backgroundColor','#F8F8F8');
                st.focus();
            }
        },
        setEditLine(l) {
            this.editLine = l;
        }
    },

});
