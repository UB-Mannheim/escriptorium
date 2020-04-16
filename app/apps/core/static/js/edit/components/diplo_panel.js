var DiploPanel = BasePanel.extend({

    data() { return {
        editLine: null,
        save: false, //show save button
        updatedLines : [],
        createdLines : [],
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

        $('#diplomatic-lines').on('dragover', '.js-drop', function(ev) {
        console.log("dragover");
        });

        $('#diplomatic-lines').on('dragleave','.js-drop', function(ev) {
            console.log("dragleave");

        });

        $('#diplomatic-lines').on('drop', '.js-drop', function(ev) {
            console.log("drop");

        });


     },
    mounted() {
        Vue.nextTick(function(){
        $('#3096').on('dragstart',function(ev) {
            console.log("dragstart");

        });
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
        }
    },

});
