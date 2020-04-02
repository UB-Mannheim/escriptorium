var DiploPanel = BasePanel.extend({

    data() { return {
        editLine: null,
        save: false, //show save button
        updatedLines : [],
    };},
    components: {
        'diploline': diploLine,
    },
    created() {
        this.$on('update:transcription:content', function(linetranscription) {
            this.addtoUpdatedLines(linetranscription);

        });
     },
    methods:{
        toggleSave(){

            if(this.save){
                this.bulkUpdate();

            }
            this.save = !this.save;
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
        },
        bulkUpdate(){
            console.log("call bulkUpdate");
            this.$parent.$emit('bulk_update:transcriptions',this.updatedLines,function () {
                this.updatedLines = [];

            });

        },
        addtoUpdatedLines(lt){
            let elt = this.updatedLines.find(l => l.pk === lt.pk);
            if(elt == undefined){
            this.updatedLines.push(lt);
            }
            else {
                elt.content = lt.content;
                elt.version_updated_at = lt.version_updated_at;
            }
        }
    },

});
