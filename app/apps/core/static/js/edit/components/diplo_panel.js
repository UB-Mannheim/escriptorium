var timer ;
var DiploPanel = BasePanel.extend({
    data() { return {
        updatedLines : [],
        createdLines : [],
        movedLines:[],

    };},
    components: {
        'diploline': diploLine,
    },
    /* mounted(){
     *     Vue.nextTick(function() {
     *         var vm = this ;
     *          var el = document.getElementById('list');
     *          sortable = Sortable.create(el, {
     *             group: 'shared',
     *             multiDrag: true,
     *             multiDragKey : 'CTRL',
     *             selectedClass: "selected",
     *             animation: 150,
     *             onEnd: function(evt) {
     *                 vm.onDragginEnd(evt);
     *             }
     *     });
     *     }.bind(this));
     * }, */
    methods:{
        startEdit(ev){
            this.$parent.blockShortcuts = true;
        },
        stopEdit(ev) {
            this.$parent.blockShortcuts = false;
        },
        onDragginEnd(ev) {
            /*
            Finish dragging lines, save new positions
            */
            if(ev.newIndicies.length == 0 && ev.newIndex != ev.oldIndex){
                let pk = ev.item.querySelector('.line-content').id;
                let elt = {"pk":pk, "index":ev.newIndex};
                this.movedLines.push(elt);

            }
            else {
                for(let i=0; i< ev.newIndicies.length; i++){
                    let line = ev.newIndicies[i];
                    let pk = line.multiDragElement.querySelector('.line-content').id;
                    let index = line.index;
                    let elt = {"pk":pk, "index":index};
                    this.movedLines.push(elt);
                }
            }

            this.moveLines();
        },
        moveLines() {
            if(this.movedLines.length != 0){
                this.$parent.$emit('line:move', this.movedLines, function () {
                    this.movedLines = [];
                }.bind(this));
            }
        },
        save() {
            /*
             if some lines are modified add them to updatedlines,
               new lines add them to createdLines then save
             */
            this.addToList();
            this.bulkUpdate();
            this.bulkCreate();
        },
        setHeight() {
            this.$el.querySelector('.content-container').style.maxHeight = Math.round(this.part.image.size[1] * this.ratio) + 'px';
        },
        focusNextLine(sel, line) {
            if (line.nextSibling) {
                let range = document.createRange();
                range.setStart(line.nextSibling, 0);
                range.collapse(false);
                sel.removeAllRanges();
                sel.addRange(range);
            }
        },
        focusPreviousLine(sel, line) {
            if (line.previousSibling) {
                let range = document.createRange();
                range.setStart(line.previousSibling, 0);
                sel.removeAllRanges();
                sel.addRange(range);
            }
        },
        onKeyPress(ev) {
            // arrows  needed to avoid skipping empty lines
            if (ev.key == 'ArrowDown' && !ev.shiftKey) {
                let sel = window.getSelection();
                let div = sel.anchorNode.nodeType==Node.TEXT_NODE?sel.anchorNode.parentElement:sel.anchorNode;
                this.focusNextLine(sel, div);
                ev.preventDefault();
            } else if (ev.key == 'ArrowUp' && !ev.shiftKey) {
                let sel = window.getSelection();
                let div = sel.anchorNode.nodeType==Node.TEXT_NODE?sel.anchorNode.parentElement:sel.anchorNode;
                this.focusPreviousLine(sel, div);
                ev.preventDefault();
            } else if (ev.key == 'Enter') {
                if (window.getSelection) {
                    const selection = window.getSelection();
                    let range = selection.getRangeAt(0);
                    // push text down
                    let lineNode = range.endContainer.nodeType==Node.TEXT_NODE?range.endContainer.parentNode:range.endContainer;
                    let lines = lineNode.parentNode.childNodes;
                    let curIndex = Array.prototype.indexOf.call(lines, lineNode);
                    let nextText = lineNode.textContent.slice(range.endOffset).trim();
                    this.$children[curIndex].$el.textContent = lineNode.textContent.slice(0, range.startOffset).trim();
                    for (let i=curIndex+1; i<lines.length-1; i++) {
                        let text = nextText;
                        nextText = lines[i].textContent;
                        this.$children[i].$el.textContent = text;
                    }
                    // focus next line
                    this.focusNextLine(selection, lineNode);
                }
                ev.preventDefault();
            } else if (ev.key == 'Backspace') {
                const selection = window.getSelection();
                let range = selection.getRangeAt(0);
                if (range.startContainer != range.endContainer) {
                    // override default behavior to avoid deleting entire lines
                    let startLine = range.startContainer.nodeType==Node.TEXT_NODE?range.startContainer.parentNode:range.startContainer;
                    let endLine = range.endContainer.nodeType==Node.TEXT_NODE?range.endContainer.parentNode:range.endContainer;
                    let inRange = false;
                    for (let i=0; i<this.$children.length; i++) {
                        let line = this.$children[i].$el;
                        if (line == startLine) {
                            line.textContent = line.textContent.slice(0, range.startOffset);
                            inRange = true;
                        } else if (line == endLine) {
                            line.textContent = line.textContent.slice(range.endOffset);
                            break;
                        } else if (inRange) {
                            line.textContent = '';
                        }
                    }

                    ev.preventDefault();
                } else if (range.startOffset == 0 && range.endOffset == 0) {
                    // push text up
                    let lineNode = range.startContainer.nodeType==Node.TEXT_NODE?range.startContainer.parentNode:range.startContainer;
                    let lines = lineNode.parentNode.childNodes;
                    let curIndex = Array.prototype.indexOf.call(lines, lineNode);
                    if (curIndex > 0) {
                        // append content to previous line
                        this.$children[curIndex-1].$el.textContent += this.$children[curIndex].$el.textContent;
                        for (let i=curIndex; i<lines.length-1; i++) {
                            this.$children[i].$el.textContent = this.$children[i+1].$el.textContent;
                        }
                        this.$children[lines.length-1].$el.textContent = '';
                    }
                    ev.preventDefault();
                }
            }
        },
        bulkUpdate() {
            if(this.updatedLines.length){
                this.$parent.$emit(
                    'bulk_update:transcriptions',
                    this.updatedLines,
                    function () {
                        this.updatedLines = [];
                    }.bind(this));
            }
        },
        bulkCreate() {
            if(this.createdLines.length){
                this.$parent.$emit(
                    'bulk_create:transcriptions',
                    this.createdLines,
                    function () {
                        this.createdLines = [];
                    }.bind(this));
            }
        },
        addToList() {
            /*
               parse all lines if the content changed, add it to updated lines
             */
            for(let i=0; i<this.$children.length; i++) {
                let currentLine = this.$children[i];
                if(currentLine.line.currentTrans.content != currentLine.$el.textContent){
                    // TODO: sanitize text content?!
                    currentLine.line.currentTrans.content = currentLine.$el.textContent;
                    if(currentLine.line.currentTrans.pk) {
                        this.addToUpdatedLines(currentLine.line.currentTrans);
                    } else {
                        this.createdLines.push(currentLine.line.currentTrans);
                    }
                }
            }
        },
        addToUpdatedLines(lt) {
            /*
            if line already exists in updatedLines update its content on the list
             */
            let elt = this.updatedLines.find(l => l.pk === lt.pk);
            if(elt == undefined) {
                this.updatedLines.push(lt);
            } else {
                elt.content = lt.content;
                elt.version_updated_at = lt.version_updated_at;
            }
        },
        updateView() {
            /*
            update the size of the panel
             */
            this.setHeight();
        },
    },

});
