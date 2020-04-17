var DiploPanel = BasePanel.extend({

    data() { return {
        editLine: null,
        save: false, //show save button
        updatedLines : [],
        createdLines : [],
        dragging: -1

    };},
    components: {
        'diploline': diploLine,
    },
    created() {
        this.$on('update:transcription:content', function(linetranscription) {
            this.addtoUpdatedLines(linetranscription);

        });
        this.$on('create:transcription', function(linetranscription) {
            this.createdLines.push(linetranscription);
        });



     },
    methods:{
        toggleSave(){
            this.bulkUpdate();
            this.bulkCreate();
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
            this.$parent.$emit('bulk_update:transcriptions',this.updatedLines,function () {
                this.updatedLines = [];
            });

        },
        bulkCreate(){
            this.$parent.$emit('bulk_create:transcriptions',this.createdLines,function () {
                this.createdLines = [];
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
        },
        dragStart(index,ev){
          ev.dataTransfer.setData('Text', "#diplomatic-lines");
          ev.target.style.border = 'solid #33A2FF';
          ev.dataTransfer.dropEffect = 'move';
           this.dragging = index;
            console.log("draaag start",ev);
        },
        dragEnd(){
            this.dragging = -1;

        },
        dragLeave(){

        },
        dragFinish(to, ev){
            ev.target.style = '';
            this.moveLine(this.dragging, to);

        },
        moveLine(from, to) {
          if (to === -1) {
            return 0;
          } else {
            this.part.lines.splice(to, 0,this.part.lines.splice(from, 1)[0]);
          }
        }

    },

});
