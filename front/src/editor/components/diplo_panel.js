import { BasePanel } from './base_panel.js';
import { diploLine } from './diplo_line.js';

export var DiploPanel = BasePanel.extend({
    data() { return {
        updatedLines : [],
        createdLines : [],
        movedLines:[],

    };},
    components: {
        'diploline': diploLine,
    },
    watch: {
        'part.loaded': function(isLoaded, wasLoaded) {
            if (!isLoaded) {
                // changed page probably
                this.empty();
            }
        }
    },
    created() {
        // vue.js quirck, have to dinamically create the event handler
        // call save every 10 seconds after last change
        this.debouncedSave = _.debounce(function() {
            this.save();
        }.bind(this), 10000);
    },
    mounted() {
        Vue.nextTick(function() {
            var vm = this ;
            vm.sortable = Sortable.create(this.editor, {
                disabled: true,
                multiDrag: true,
                multiDragKey : 'CTRL',
                selectedClass: "selected",
                ghostClass: "ghost",
                dragClass: "info",
                animation: 150,
                onEnd: function(evt) {
                    vm.onDraggingEnd(evt);
                }
            });
        }.bind(this));

        this.editor = this.$el.querySelector('#diplomatic-lines');
        this.sortModeBtn = this.$el.querySelector('#sortMode');
        this.saveNotif = this.$el.querySelector('.tools #save-notif');
        this.refresh();
    },
    methods: {
        empty() {
            while (this.editor.hasChildNodes()) {
                this.editor.removeChild(this.editor.lastChild);
            }
        },
        toggleSort() {
            if (this.editor.contentEditable === 'true') {
                this.editor.contentEditable = 'false';
                this.sortable.option('disabled', false);
                this.sortModeBtn.classList.remove('btn-info');
                this.sortModeBtn.classList.add('btn-success');
            } else {
                this.editor.contentEditable = 'true';
                this.sortable.option('disabled', true);
                this.sortModeBtn.classList.remove('btn-success');
                this.sortModeBtn.classList.add('btn-info');
            }
        },
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
                this.editor.insertBefore(div, pos);
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
        onDraggingEnd(ev) {
            /*
               Finish dragging lines, save new positions
             */
            if(ev.newIndicies.length == 0 && ev.newIndex != ev.oldIndex) {
                let diploLine = this.$children.find(dl=>dl.line.order==ev.oldIndex);
                this.movedLines.push({
                    "pk": diploLine.line.pk,
                    "order": ev.newIndex
                });
            } else {
                for(let i=0; i< ev.newIndicies.length; i++) {

                    let diploLine = this.$children.find(dl=>dl.line.order==ev.oldIndicies[i].index);
                    this.movedLines.push({
                        "pk": diploLine.line.pk,
                        "order": ev.newIndicies[i].index
                    });
                }
            }
            this.moveLines();
        },
        moveLines() {
            if(this.movedLines.length != 0){
                this.$parent.$emit('move:line', this.movedLines, function () {
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
        focusNextLine(sel, line) {
            if (line.nextSibling) {
                let range = document.createRange();
                range.setStart(line.nextSibling, 0);
                range.collapse(false);
                sel.removeAllRanges();

                if (line.nextSibling.offsetTop >
                    this.editor.parentNode.scrollTop + this.editor.parentNode.clientHeight) {
                    line.nextSibling.scrollIntoView(false);
                }

                sel.addRange(range);
            }
        },
        focusPreviousLine(sel, line) {
            if (line.previousSibling) {
                let range = document.createRange();
                range.setStart(line.previousSibling, 0);
                sel.removeAllRanges();

                if (line.previousSibling.offsetTop - this.editor.parentNode.offsetTop <
                    this.editor.parentNode.scrollTop) {
                    line.previousSibling.scrollIntoView(true);
                }

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
            var tmp = document.createElement("div");
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
                let start = Array.prototype.indexOf.call(this.editor.children, target);
                let newDiv, child = this.editor.children[start];
                for (let i = 0; i < pasted_data_split.length; i++) {
                    newDiv = this.appendLine(child);
                    newDiv.textContent = this.cleanSource(pasted_data_split[i]);
                    // trick to get at least 'some' ctrl+z functionality
                    // this fails in spectacular ways differently in firefox and chrome... so no ctrl+z
                    /* range.setStart(newDiv, 0);
                     * selection.removeAllRanges();
                     * selection.addRange(range);
                     * document.execCommand("insertText", false, this.cleanSource(content)); */
                }
            }

            this.constrainLineNumber();
            e.preventDefault();
        },
        showOverlay(ev) {
            let target = ev.target.nodeType==Node.TEXT_NODE?ev.target.parentNode:ev.target;
            let index = Array.prototype.indexOf.call(target.parentNode.children, target);
            if (index > -1 && index < this.$children.length) {
                let diploLine = this.$children.find(dl=>dl.line.order==index);
                if (diploLine) diploLine.showOverlay();
            } else {
                this.hideOverlay();
            }
        },
        hideOverlay() {
            if (this.$children.length) this.$children[0].hideOverlay();
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
                let content = currentLine.getEl().textContent;
                if(currentLine.line.currentTrans.content != content){
                    currentLine.line.currentTrans.content = content;
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
        setHeight() {
            this.$el.querySelector('.content-container').style.minHeight = Math.round(this.part.image.size[1] * this.ratio) + 'px';
        },
        updateView() {
            this.setHeight();
        }
    }
});
