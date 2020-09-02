var DiploPanel = BasePanel.extend({
    data() { return {
        updatedLines : [],
        createdLines : [],
        movedLines:[],

    };},
    components: {
        'diploline': diploLine,
    },
    created() {
        // vue.js quirck, have to dinamically create the event handler
        // call save every 10 seconds after last change
        this.debouncedSave = _.debounce(function() {
            this.save();
        }.bind(this), 10000);
    },
    mounted() {
        /*     Vue.nextTick(function() {
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
         */
        this.editor = this.$el.querySelector('#diplomatic-lines');
        this.saveNotif = this.$el.querySelector('.tools #save-notif');
    },
    methods: {
        changed() {
            this.saveNotif.classList.remove('hide');
            this.debouncedSave();
        },
        appendLine(pos) {
            let div = document.createElement('div');
            div.appendChild(document.createElement('br'));
            if (pos === undefined) {
                this.editor.appendChild(div);
            } else {
                this.editor.insertBefore(div, pos.nextSibling);
            }
            return div;
        },
        constrainLineNumber() {
            // add lines untill we have enough of them
            while (this.editor.childElementCount < this.part.lines.length) {
                this.appendLine();
            }

            // need to add/remove danger indicators
            for (let i=0; i<this.editor.childElementCount; i++) {
                let line = this.editor.querySelector('div:nth-child('+parseInt(i+1)+')');
                if (line === null) {
                    this.editor.children[i].remove();
                    continue;
                }

                if (i<this.part.lines.length) {
                    line.classList.remove('alert-danger');
                    line.setAttribute('title', '');
                } else if (i>=this.part.lines.length) {
                    if (line.textContent == '') { // just remove empty lines
                        line.remove();
                    } else  {
                        line.classList.add('alert-danger');
                        line.setAttribute('title', 'More lines than there is in the segmentation!');
                    }
                }
            }
        },
        startEdit(ev) {
            this.$parent.blockShortcuts = true;
        },
        stopEdit(ev) {
            this.$parent.blockShortcuts = false;
            this.constrainLineNumber();
            this.save();
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
            this.saveNotif.classList.add('hide');
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
            }
        },
        cleanSource(dirtyText) {
            // cleanup html and possibly other tags (?)
            var tmp = document.createElement("DIV");
            tmp.innerHTML = dirtyText;
            let clean = tmp.textContent || tmp.innerText || "";
            tmp.remove();
            return clean;
        },
        onPaste(e) {
            let pastedData = e.clipboardData.getData('text/plain');
            let pasted_data_split = pastedData.split('\n');

            if (pasted_data_split.length == 1) {
                let content = this.cleanSource(pastedData);
                document.execCommand('insertText', false, content);
            } else {
                const selection = window.getSelection();
                let range = selection.getRangeAt(0);
                let target = range.startContainer.nodeType==Node.TEXT_NODE?range.startContainer.parentNode:range.startContainer;
                let start = Array.prototype.indexOf.call(target.parentNode.children, target);
                for (let i = 0; i < pasted_data_split.length; i++) {
                    let content = pasted_data_split[i];
                    let child = target.parentNode.children[start+i];
                    let newDiv;
                    if (child) {
                        newDiv = this.appendLine(child);
                    } else {
                        newDiv = this.appendLine();
                    }
                    // trick to get at least 'some' ctrl+z functionality
                    range.setStart(newDiv, 0);
                    selection.removeAllRanges();
                    selection.addRange(range);
                    document.execCommand("insertText", false, this.cleanSource(content));
                }
            }

            this.constrainLineNumber();
            e.preventDefault();
        },
        showOverlay(ev) {
            let target = ev.target.nodeType==Node.TEXT_NODE?ev.target.parentNode:ev.target;
            let index = Array.prototype.indexOf.call(target.parentNode.children, target);
            if (index > -1 && index < this.$children.length) {
                this.$children[index].showOverlay();
            } else {
                this.hideOverlay();
            }
        },
        hideOverlay() {
            this.$children[0].hideOverlay();
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
                if(currentLine.line.currentTrans.content != currentLine.getEl().textContent){
                    currentLine.line.currentTrans.content = currentLine.getEl().textContent;
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
