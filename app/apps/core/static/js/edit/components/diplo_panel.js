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
        editNext() {
            ev.preventDefault();
            // TODO
            console.log("call editableContent",this.$parent);
        },
    },

});
