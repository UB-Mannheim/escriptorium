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
                    autocomplete="off"></button>
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
        // fix the original width so that when content texts are loaded/page refreshed with diplo panel, the panel width wont be bigger than other, especially for ttb text:
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
            return div;
        },
        constrainLineNumber() {
            // add lines untill we have enough of them
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
            var types, pastedData, savedContent;
            
            // Browsers that support the 'text/html' type in the Clipboard API (Chrome, Firefox 22+)
            if (e && e.clipboardData && e.clipboardData.types && e.clipboardData.getData) {
                types = e.clipboardData.types;
                if (((types instanceof DOMStringList) && types.contains("text/html")) || (types.indexOf && types.indexOf('text/html') !== -1)) {      
                    // Extract data and pass it to callback
                    pastedData = e.clipboardData.getData('text/html');
                    //pastedData = e.clipboardData.getData('text/plain');
                    this.processPaste(diplomaticLines, pastedData);

                    // Stop the data from actually being pasted
                    e.stopPropagation();
                    e.preventDefault();
                    return false;
                }else  {

                    // Extract data and pass it to callback
                    pastedData = e.clipboardData.getData('text/plain');
                    //pastedData = e.clipboardData.getData('text/plain');
                    this.processPaste(diplomaticLines, pastedData);

                    // Stop the data from actually being pasted
                    e.stopPropagation();
                    e.preventDefault();
                    return false;
                }
            }
            
            // Everything else: Move existing element contents to a DocumentFragment for safekeeping
            savedContent = document.createDocumentFragment();
            while(diplomaticLines.childNodes.length > 0) {
                savedContent.appendChild(diplomaticLines.childNodes[0]);
            }
            
            // Then wait for browser to paste content into it and cleanup
            this.waitForPastedData(diplomaticLines, savedContent);
            return true;
        },
        processPaste(diplomaticLines, replacementText)
        {
            // store initial number of segemnted lines:
            let nativeNumberOfLines = diplomaticLines.getElementsByTagName('div').length;

            let sel;
            if (window.getSelection) {
                sel = window.getSelection();

                if (sel.rangeCount) 
                {               
                    // put the replacementn text into a div element to manage content as tags
                    let tmpDiv = document.createElement('div');
                    let textLines = new Array();
                    tmpDiv.innerHTML = replacementText; //  important sile texte à récupérer est au format html

                    // convert html/plain text CR into a normalized separator ([CR]):
                    let divs = tmpDiv.getElementsByTagName("div");
                    if(divs.length > 0) //  some html content, mainly from another transcription panel
                    {
                        for(var i=0;i<divs.length;i++)
                        {
                            textLines.push(divs[i].textContent + '[CR]');
                        }
                    }else{  //  plain text with some included CR chars
                        var regCR = new RegExp("[\r]{0,1}\n", "g");
                        var plainTextLines =  replacementText.split(regCR);

                        for(var i=0;i<plainTextLines.length;i++)
                        {
                            textLines.push(plainTextLines[i] + '[CR]');
                        }
                    }
                    replacementText = textLines.join('');

                    // place this text as content of a div
                    var newNode = document.createElement('div'); newNode.innerHTML = replacementText; 
                    var cursor = sel.getRangeAt(0);  
                    cursor.deleteContents(); 
                    // paste text on the selection (cursor position or range):
                    cursor.insertNode(newNode); 
                    
                    // convert the whole html text lines into a single string with normalized separator ([CR])
                    let content = '';
                    tmpDiv.innerHTML = diplomaticLines.innerHTML;
                    divs = tmpDiv.getElementsByTagName("div");
                    var numberOfLines = divs.length;
                    var indexLine = 0;
                    var currentDiv;
                    while(typeof(divs[0]) != "undefined")
                    {
                        currentDiv = divs[0];
                        var innerContent = currentDiv.textContent;
                        content += innerContent;

                        // add a CR char for each div/ only if not last line and does not contain a CR char at the end:
                        if((indexLine < numberOfLines-1)&&(innerContent.substring(innerContent.length - 4) != '[CR]'))
                            content += '[CR]';
                        // to avoid doublons, we remove each div tag from tmpDiv:
                        currentDiv.parentNode.removeChild(currentDiv);
                        indexLine++;
                    }

                    // convert each new line into a div element
                    textLines = content.split('[CR]');
                    tmpDiv.innerHTML = '';
                    for(var i=0;i<textLines.length;i++)
                    {
                        tmpDiv.innerHTML +='<div title="">'+textLines[i]+'</div>';
                    }

                    // update panel content! :
                    diplomaticLines.innerHTML = tmpDiv.innerHTML;   
                }
            } else if (document.selection && document.selection.createRange) {
                
                range = document.selection.createRange();
                range.text = replacementText;
            }
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
        }
    }
});
</script>

<style scoped>
</style>
