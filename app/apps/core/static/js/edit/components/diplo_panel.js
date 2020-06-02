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
            this.addToUpdatedLines(linetranscription);
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
        setHeight() {
            this.$el.querySelector('.content-container').style.maxHeight = Math.round(this.part.image.size[1] * this.ratio) + 'px';
        },
        editNext(ev) {
            ev.preventDefault();
            let index = this.part.lines.indexOf(this.editLine);
            if(index < this.part.lines.length - 1) {
                this.setEditLine(this.part.lines[index + 1]);
                let nextLine = this.$children[index + 1];
                nextLine.startEdit();
            }
        },
        setEditLine(l) {
            this.editLine = l;
        },
        bulkUpdate(){
            if(this.updatedLines.length){
                this.$parent.$emit(
                    'bulk_update:transcriptions',
                    this.updatedLines,
                    function () {
                        this.updatedLines = [];
                    }.bind(this));
            }
        },
        bulkCreate(){
            if(this.createdLines.length){
                this.$parent.$emit(
                    'bulk_create:transcriptions',
                    this.createdLines,
                    function () {
                        this.createdLines = [];
                        this.createdLines.splice(0, this.createdLines.length);
                    }.bind(this));
            }
        },
        addToUpdatedLines(lt){
            let elt = this.updatedLines.find(l => l.pk === lt.pk);
            if(elt == undefined) {
                this.updatedLines.push(lt);
            } else {
                elt.content = lt.content;
                elt.version_updated_at = lt.version_updated_at;
            }
        },
        dragStart(line,ev){
            ev.dataTransfer.setData('Text', "#diplomatic-lines");
            ev.target.style.border = 'solid #33A2FF';
            ev.dataTransfer.dropEffect = 'move';
            let index = this.part.lines.indexOf(line);
            this.dragging = index;
            // console.log("draaag start",index);
        },
        dragEnd(){
            this.dragging = -1;
        },
        dragFinish(line, ev){
            let to = this.part.lines.indexOf(line);
            ev.target.style = '';
            this.moveLine(this.dragging, to);
            // this.part.recalculateOrdering();
            this.$parent.$emit('line:move_to',line.pk,to, function () {
                // this.$children[to].line.order = to ;
                this.$set(this.$children[to].line.order,to);
            }.bind(this));
        },
        moveLine(from, to) {
            if (to === -1) {
                return 0;
            } else {
                this.part.lines.splice(to, 0,this.part.lines.splice(from, 1)[0]);
            }
        },
        updateView() {
            this.setHeight();
        },
    },
});
