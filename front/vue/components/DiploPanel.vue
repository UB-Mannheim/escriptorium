<template>
    <div class="col panel">
        <div class="tools">
            <i title="Text Panel" class="panel-icon fas fa-list-ol"></i>
            <i id="save-notif" ref="saveNotif" title="There is content waiting to be saved (don't leave the page)" class="notice fas fa-save hide"></i>
            <button id="sortMode"
                    ref="sortMode"
                    title="Toggle sorting mode."
                    class="btn btn-sm ml-3 btn-info fas fa-sort"
                    @click="toggleSort"
                    autocomplete="off"
                    :disabled="isVKEnabled"></button>
            <button class="btn btn-sm ml-2 mr-1"
                    :class="{'btn-info': isVKEnabled, 'btn-outline-info': !isVKEnabled}"
                    title="Toggle Virtual Keyboard for this document."
                    @click="toggleVK">
                <i class="fas fa-keyboard"></i>
            </button>
        </div>
        <div :class="'content-container ' + $store.state.document.readDirection" ref="contentContainer">

            <diploline v-for="line in $store.state.lines.all"
                        v-bind:line="line"
                        v-bind:ratio="ratio"
                        v-bind:key="'DL' + line.pk">
            </diploline>

            <!--adding a class to get styles for ttb direction:-->
            <div :class="$store.state.document.mainTextDirection"
                    id="diplomatic-lines"
                    ref="diplomaticLines"
                    contenteditable="true"
                    autocomplete="off"
                    @keydown="onKeyPress"
                    @keyup="constrainLineNumber"
                    @input="changed"
                    @focusin="startEdit"
                    @focusout="stopEdit"
                    @paste="onPaste"
                    @mousemove="showOverlay"
                    @mouseleave="hideOverlay">
            </div>
        </div>
    </div>
</template>

<script>
import { BasePanel } from '../../src/editor/mixins.js';
import DiploLine from './DiploLine.vue';

export default Vue.extend({
    mixins: [BasePanel],
    data() { return {
        updatedLines : [],
        createdLines : [],
        movedLines:[],
        isVKEnabled: false,
    };},
    components: {
        'diploline': DiploLine,
    },
    watch: {
        '$store.state.parts.loaded': function(isLoaded, wasLoaded) {
            if (!isLoaded) {
                // changed page probably
                this.empty();
            }
        },
        '$store.state.document.enabledVKs'() {
            this.isVKEnabled = this.$store.state.document.enabledVKs.indexOf(this.$store.state.document.id) != -1 || false;
        }
    },
    created() {
        // vue.js quirck, have to dynamically create the event handler
        // call save every 10 seconds after last change
        this.debouncedSave = _.debounce(function() {
            this.save();
        }.bind(this), 10000);
    },
    mounted() {
        // fix the original width so that when content texts are loaded/page refreshed with diplo panel, the panel width won't be bigger than other, especially for ttb text:
        document.querySelector('#diplo-panel').style.width = document.querySelector('#diplo-panel').clientWidth + 'px';

        Vue.nextTick(function() {
            var vm = this ;
            vm.sortable = Sortable.create(this.$refs.diplomaticLines, {
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

        this.refresh();

        this.isVKEnabled = this.$store.state.document.enabledVKs.indexOf(this.$store.state.document.id) != -1 || false;
    },
    methods: {
        empty() {
            while (this.$refs.diplomaticLines.hasChildNodes()) {
                this.$refs.diplomaticLines.removeChild(this.$refs.diplomaticLines.lastChild);
            }
        },
        toggleSort() {
            if (this.$refs.diplomaticLines.contentEditable === 'true') {
                this.$refs.diplomaticLines.contentEditable = 'false';
                this.sortable.option('disabled', false);
                this.$refs.sortMode.classList.remove('btn-info');
                this.$refs.sortMode.classList.add('btn-success');
            } else {
                this.$refs.diplomaticLines.contentEditable = 'true';
                this.sortable.option('disabled', true);
                this.$refs.sortMode.classList.remove('btn-success');
                this.$refs.sortMode.classList.add('btn-info');
            }
        },
        changed() {
            this.$refs.saveNotif.classList.remove('hide');
            this.debouncedSave();
        },
        appendLine(pos) {
            let div = document.createElement('div');
            div.appendChild(document.createElement('br'));
            if (pos === undefined) {
                this.$refs.diplomaticLines.appendChild(div);
            } else {
                this.$refs.diplomaticLines.insertBefore(div, pos);
            }
            if (this.isVKEnabled) {
                this.activateVK(div);
            }
            return div;
        },
        constrainLineNumber() {
            // add lines until we have enough of them
            while (this.$refs.diplomaticLines.childElementCount < this.$store.state.lines.all.length) {
                this.appendLine();
            }

            // need to add/remove danger indicators
            for (let i=0; i<this.$refs.diplomaticLines.childElementCount; i++) {
                let line = this.$refs.diplomaticLines.querySelector('div:nth-child('+parseInt(i+1)+')');
                if (line === null) {
                    this.$refs.diplomaticLines.children[i].remove();
                    continue;
                }

                if (i<this.$store.state.lines.all.length) {
                    line.classList.remove('alert-danger');
                    line.setAttribute('title', '');
                } else if (i>=this.$store.state.lines.all.length) {
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
            this.$store.commit('document/setBlockShortcuts', true);
        },
        stopEdit(ev) {
            this.$store.commit('document/setBlockShortcuts', false);
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
        async moveLines() {
            if(this.movedLines.length != 0) {
                try {
                    await this.$store.dispatch('lines/move', this.movedLines)
                    this.movedLines = []
                } catch (err) {
                    console.log('couldnt recalculate order of line', err)
                }
            }
        },
        save() {
            /*
               if some lines are modified add them to updatedlines,
               new lines add them to createdLines then save
             */
            this.$refs.saveNotif.classList.add('hide');
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
                    this.$refs.contentContainer.scrollTop + this.$refs.contentContainer.clientHeight) {
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

                if (line.previousSibling.offsetTop - this.$refs.contentContainer.offsetTop <
                    this.$refs.contentContainer.scrollTop) {
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
            
            let diplomaticLines=document.querySelector("#diplomatic-lines");
            let sel = window.getSelection();
            let tmpDiv = document.createElement('div');

            let pastedData;
            if (e && e.clipboardData && e.clipboardData.types && e.clipboardData.getData) {
                let types = e.clipboardData.types;
                if (((types instanceof DOMStringList) && types.contains("text/html")) || (types.indexOf && types.indexOf('text/html') !== -1)) {
                    let content = e.clipboardData.getData('text/html');
                    tmpDiv.innerHTML = content;
                    pastedData = [ ...tmpDiv.childNodes].map(e=>e.textContent).join('\n');
                } else {
                    pastedData = e.clipboardData.getData('text/plain');
                }
                
                var cursor = sel.getRangeAt(0);  // specific posiiton or range
                // for a range, delete content to clean data and to get resulting specific cursor position from it:
                cursor.deleteContents(); // if selection is done on several lines, cursor caret be placed between 2 divs

                // after deleting (for an range), 
                // check if resulting cursor is in or off a line div or some errors will occur!:
                let parentEl = sel.getRangeAt(0).commonAncestorContainer; 
                if (parentEl.nodeType != 1) {
                    parentEl = parentEl.parentNode;   //  for several different lines, commonAncestorContainer does not exist
                }

                let pasted_data_split = pastedData.split("\n");
                let refNode = parentEl;

                let textBeforeCursor = '';
                let textAfterCursor = '';

                // nodes which will be placed before and after the targetnode - where text is pasted (new node or current node)
                let prevSibling;
                let nextSibling;

                if(parentEl.id == 'diplomatic-lines'){  //  if parent node IS the main diplomatic panel div = cursor is offline
                    // occurs when a selection is made on several lines or all is selected

                    //we create a between node:
                    refNode = document.createElement('div'); 
                    refNode.textContent = '';

                    // paste text on the selection (cursor position or range):
                    cursor.insertNode(refNode);

                    // set caret position/place the cursor into the new node:
                    cursor.setStart(refNode,0);
                    cursor.setEnd(refNode,0);

                    // in this case, contents before and after selection will belong to near siblings
                    if(refNode.previousSibling != null){
                        prevSibling = refNode.previousSibling;
                    }
                    if(refNode.nextSibling != null){
                        nextSibling = refNode.nextSibling;
                    }
                }

                //  get current cursor position within the line div tag
                let caretPos = cursor.endOffset;    //  4   //  nombre de caractères du début jusqu'à la position du curseur             

                // store previous and next text in the line to it / for a selection within on line:
                textBeforeCursor = refNode.textContent.substring(0, caretPos);
                textAfterCursor = refNode.textContent.substring(caretPos, refNode.textContent.length);

                // for a selection between several lines, contents before and after will be the contents of siblings
                // to avoid create new lines before and after, fusion of sibling contents to the current node and removing it
                if(typeof(prevSibling) != "undefined"){
                    textBeforeCursor = prevSibling.textContent;
                    prevSibling.parentNode.removeChild(prevSibling);
                }
                if(typeof(nextSibling) != "undefined"){
                    textAfterCursor = nextSibling.textContent;
                    nextSibling.parentNode.removeChild(nextSibling);
                }
                
                let endPos = 0; //  will set the new cursor position
                let lastTargetNode = refNode;   //  last impacted node for a copy-paste (for several lines)

                if(pasted_data_split.length == 1){
                    refNode.textContent = textBeforeCursor + pasted_data_split[0] + textAfterCursor;
                    endPos = String(textBeforeCursor + pasted_data_split[0]).length;
                }
                else{
                    // store resulting firstLine & lastLine contents regarding cursor position
                    let firstLine = textBeforeCursor + pasted_data_split[0];
                    let lastLine = pasted_data_split[pasted_data_split.length -1] + textAfterCursor; 
                    let nextNodesContents = new Array();

                    for(var j=0; j < pasted_data_split.length; j++) 
                    {
                        var lineContent = pasted_data_split[j];
                        if(j == 0) 
                            lineContent = firstLine;
                        if(j == pasted_data_split.length-1)
                            lineContent = lastLine;
                        nextNodesContents.push(lineContent);                                                
                    }
                    // get length of last pasted line to set new caret position
                    endPos = String(pasted_data_split[pasted_data_split.length-1]).length;
                    
                    refNode.textContent = nextNodesContents[nextNodesContents.length-1];
                    lastTargetNode = refNode;
                    
                    nextNodesContents = nextNodesContents.reverse();

                    for(var j=1; j < nextNodesContents.length; j++) //  for any other line, we add a div and set this content
                    {
                        var prevLineDiv = document.createElement('div');
                        prevLineDiv.textContent = nextNodesContents[j];
                        // add the new line as a next neighbor of current div:
                        refNode = diplomaticLines.insertBefore(prevLineDiv, refNode);
                    }
                }
                // set the caret position right after the pasted content:

                if(typeof(lastTargetNode.childNodes[0]) != "undefined")
                {
                    let textNode = lastTargetNode.childNodes[0];
                    cursor.setStart(textNode, endPos);
                }

            } else {
                // not sure if this can actually happen in firefox/chrome?!
                pastedData = "";
                // so we do nothing; keeping original content
            }

            // Stop the data from actually being pasted //  without it will paste the native copied text after "content"
            e.stopPropagation();
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

        async bulkUpdate() {
            if(this.updatedLines.length){
                await this.$store.dispatch('transcriptions/bulkUpdate', this.updatedLines);
                this.updatedLines = [];
            }
        },
        async bulkCreate() {
            if(this.createdLines.length){
                await this.$store.dispatch('transcriptions/bulkCreate', this.createdLines);
                this.createdLines = [];
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
            this.$refs.contentContainer.style.minHeight = Math.round(this.$store.state.parts.image.size[1] * this.ratio) + 'px';
        },
        updateView() {
            this.setHeight();
        },
        activateVK(div) {
            div.contentEditable = 'true';
            this.$refs.diplomaticLines.contentEditable = 'false';
            enableVirtualKeyboard(div);
        },
        deactivateVK(div) {
            div.removeAttribute('contentEditable');
            this.$refs.diplomaticLines.contentEditable = 'true';
            div.onfocus = (e) => { e.preventDefault() };
        },
        toggleVK() {
            this.isVKEnabled = !this.isVKEnabled;
            let vks = this.$store.state.document.enabledVKs;
            if (this.isVKEnabled) {
                vks.push(this.$store.state.document.id);
                this.$store.commit('document/setEnabledVKs', vks);
                userProfile.set("VK-enabled", vks);
                this.$refs.diplomaticLines.childNodes.forEach(c => {
                    this.activateVK(c);
                });
            } else {
                // Make sure we save changes made before we remove the VK
                vks.splice(vks.indexOf(this.$store.state.document.id), 1);
                this.$store.commit('document/setEnabledVKs', vks);
                userProfile.set("VK-enabled", vks);
                this.$refs.diplomaticLines.childNodes.forEach(c => {
                    this.deactivateVK(c);
                });
            }
        }
    }
});
</script>

<style scoped>
</style>
