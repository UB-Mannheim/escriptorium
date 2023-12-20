<template>
    <div
        id="diplo-panel"
        class="col panel"
    >
        <div
            v-if="legacyModeEnabled"
            class="tools"
        >
            <i
                title="Text Panel"
                class="panel-icon fas fa-list-ol"
            />
            <i
                id="save-notif"
                ref="saveNotif"
                title="There is content waiting to be saved (don't leave the page)"
                class="notice fas fa-save hide"
            />
            <button
                id="sortMode"
                ref="sortMode"
                title="Toggle sorting mode."
                class="btn btn-sm ml-3 btn-info fas fa-sort"
                autocomplete="off"
                :disabled="isVKEnabled"
                @click="toggleSort"
            />

            <button
                class="btn btn-sm ml-2"
                :class="{'btn-info': isVKEnabled, 'btn-outline-info': !isVKEnabled}"
                title="Toggle Virtual Keyboard for this document."
                @click="toggleVK"
            >
                <i class="fas fa-keyboard" />
            </button>

            <div
                v-for="(typo, idx) in groupedTaxonomies"
                :key="idx"
                class="btn-group taxo-group ml-2 mr-1"
            >
                <button
                    v-for="taxo in typo"
                    :id="'anno-taxo-' + taxo.pk"
                    :key="taxo.pk"
                    :data-taxo="taxo"
                    :title="taxo.name"
                    class="btn btn-sm btn-outline-info"
                    autocomplete="off"
                    @click="toggleTaxonomy(taxo)"
                >
                    {{ taxo.abbreviation ? taxo.abbreviation : taxo.name }}
                </button>
            </div>
        </div>
        <EditorToolbar
            v-else
            panel-type="diplomatic"
            :disabled="disabled"
            :panel-index="panelIndex"
        >
            <template #editor-tools-center>
                <div class="escr-editortools-paneltools">
                    <!-- transcription switcher -->
                    <TranscriptionDropdown
                        :disabled="disabled"
                    />

                    <!-- Line reordering -->
                    <VDropdown
                        theme="escr-tooltip-small"
                        placement="bottom"
                        :distance="8"
                        :triggers="['hover']"
                    >
                        <ToggleButton
                            color="secondary"
                            class="sort-mode-toggle"
                            :checked="isSortModeEnabled"
                            :disabled="disabled || isVKEnabled"
                            :on-change="toggleSort"
                        >
                            <template #button-icon>
                                <LineOrderingIcon />
                            </template>
                        </ToggleButton>
                        <template #popper>
                            Line ordering mode
                        </template>
                    </VDropdown>

                    <i
                        id="save-notif"
                        ref="saveNotif"
                        title="There is content waiting to be saved (don't leave the page)"
                        class="notice fas fa-save hide new-section"
                    />

                    <!-- Virtual keyboard -->
                    <div class="vk-container">
                        <VDropdown
                            theme="escr-tooltip-small"
                            placement="bottom"
                            :distance="8"
                            :triggers="['hover']"
                        >
                            <ToggleButton
                                :checked="isVKEnabled"
                                :disabled="disabled"
                                :on-change="toggleVK"
                            >
                                <template #button-icon>
                                    <KeyboardIcon />
                                </template>
                            </ToggleButton>
                            <template #popper>
                                Virtual keyboard
                            </template>
                        </VDropdown>
                    </div>
                </div>
            </template>
        </EditorToolbar>
        <div
            v-if="!legacyModeEnabled && (
                annotationTaxonomies &&
                annotationTaxonomies.text &&
                annotationTaxonomies.text.length > 0
            )"
            ref="annotationToolbar"
            class="escr-annotation-toolbar"
        >
            <div
                v-for="(typo, idx) in groupedTaxonomies"
                :key="idx"
                class="escr-anno-group"
            >
                <VDropdown
                    v-for="taxo in typo"
                    :key="taxo.pk"
                    theme="escr-tooltip-small"
                    placement="bottom"
                    :distance="8"
                    :triggers="['hover']"
                >
                    <button
                        :id="'anno-taxo-' + taxo.pk"
                        :style="{
                            backgroundColor: currentTaxonomy == taxo
                                ? taxo.marker_detail
                                : `${taxo.marker_detail}CC`,
                        }"
                        :class="{
                            'escr-anno-pill': true,
                            'selected': currentTaxonomy == taxo,
                        }"
                        autocomplete="off"
                        @click="() => toggleTaxonomy(taxo)"
                    >
                        {{ taxo.abbreviation ? taxo.abbreviation : taxo.name }}
                    </button>
                    <template #popper>
                        {{ taxo.name }}
                    </template>
                </VDropdown>
            </div>
        </div>
        <div
            ref="contentContainer"
            :class="'content-container ' + $store.state.document.readDirection"
        >
            <DiploLine
                v-for="line in allLines"
                ref="diploLineComponents"
                :key="'DL' + line.pk"
                :line="line"
                :ratio="ratio"
            />

            <!--adding a class to get styles for ttb direction:-->
            <div
                id="diplomatic-lines"
                ref="diplomaticLines"
                :class="{ [mainTextDirection]: true, sortmode: isSortModeEnabled }"
                contenteditable="true"
                autocomplete="off"
                @keydown="onKeyPress"
                @keyup="constrainLineNumber"
                @input="changed"
                @focusin="startEdit"
                @focusout="stopEdit"
                @paste="onPaste"
                @mousemove="showOverlay"
                @mouseleave="hideOverlay"
            />
        </div>
    </div>
</template>

<script>
import { nextTick } from "vue";
import { mapActions, mapMutations, mapState } from "vuex";
import { Dropdown as VDropdown } from "floating-vue";
import { Recogito } from "@recogito/recogito-js";
import { BasePanel , AnnoPanel } from "../../src/editor/mixins.js";
import KeyboardIcon from "./Icons/KeyboardIcon/KeyboardIcon.vue";
import LineOrderingIcon from "./Icons/LineOrderingIcon/LineOrderingIcon.vue";
import DiploLine from "./DiploLine.vue";
import EditorToolbar from "./EditorToolbar/EditorToolbar.vue";
import ToggleButton from "./ToggleButton/ToggleButton.vue";
import TranscriptionDropdown from "./EditorTranscriptionDropdown/EditorTranscriptionDropdown.vue";
import "../components/Common/Annotation.css";

export default {
    components: {
        DiploLine,
        EditorToolbar,
        KeyboardIcon,
        LineOrderingIcon,
        ToggleButton,
        TranscriptionDropdown,
        VDropdown,
    },
    mixins: [BasePanel, AnnoPanel],
    data() {
        return {
            updatedLines : [],
            createdLines : [],
            movedLines:[],
            isVKEnabled: false,
            isSortModeEnabled: false,
        };
    },
    computed: {
        ...mapState({
            allLines: (state) => state.lines.all,
            allTextAnnotations: (state) => state.textAnnotations.all,
            annotationTaxonomies: (state) => state.document.annotationTaxonomies,
            documentId: (state) => state.document.id,
            enabledVKs: (state) => state.document.enabledVKs,
            mainTextDirection: (state) => state.document.mainTextDirection,
            selectedTranscription: (state) => state.transcriptions.selectedTranscription,
            transcriptionsLoaded: (state) => state.transcriptions.transcriptionsLoaded,
            partsLoaded: (state) => state.parts.loaded,
        }),
        groupedTaxonomies() {
            // eslint-disable-next-line no-undef
            return _.groupBy(
                this.annotationTaxonomies.text,
                (taxo) => taxo.typology && taxo.typology.name,
            );
        }
    },
    watch: {
        partsLoaded(isLoaded) {
            if (!isLoaded) {
                // changed page probably
                this.empty();
            }
        },
        enabledVKs() {
            this.isVKEnabled = this.enabledVKs.indexOf(this.documentId) != -1 || false;
        },
        transcriptionsLoaded(isLoaded) {
            if (isLoaded === true) {
                this.loadAnnotations();
            }
        }
    },

    created() {
        // vue.js quirck, have to dynamically create the event handler
        // call save every 10 seconds after last change
        // eslint-disable-next-line no-undef
        this.debouncedSave = _.debounce(function() {
            this.save();
        }.bind(this), 10000);
    },

    mounted() {
        if (this.legacyModeEnabled) {
            // fix the original width so that when content texts are loaded/page refreshed with
            // diplo panel, the panel width won't be bigger than other, especially for ttb text:
            const clientWidth = document.querySelector("#diplo-panel").clientWidth;
            document.querySelector("#diplo-panel").style.width = `${clientWidth}px`;
        } else if (this.$refs.annotationToolbar && this.$refs.contentContainer) {
            // ensure panel height takes anno toolbar into account, and does so again on resize
            this.recalculatePanelHeight();
            window.addEventListener("resize", this.recalculatePanelHeight);
        }
        nextTick(function() {
            var vm = this ;
            // eslint-disable-next-line no-undef
            vm.sortable = Sortable.create(this.$refs.diplomaticLines, {
                disabled: true,
                multiDrag: true,
                multiDragKey : "Meta",
                selectedClass: "selected",
                ghostClass: "ghost",
                dragClass: "info",
                animation: 150,
                onEnd: function(evt) {
                    vm.onDraggingEnd(evt);
                }
            });

            // update heights and set ratio
            this.refresh();
        }.bind(this));

        this.initAnnotations();

        this.isVKEnabled = this.enabledVKs.indexOf(this.documentId) != -1 || false;
    },

    methods: {
        ...mapActions("textAnnotations", {
            createTextAnnotation: "create",
            deleteTextAnnotation: "delete",
            fetchTextAnnotations: "fetch",
            updateTextAnnotation: "update",
        }),
        ...mapMutations("document", ["setBlockShortcuts"]),

        empty() {
            this.anno.clearAnnotations();
            while (this.$refs.diplomaticLines.hasChildNodes()) {
                this.$refs.diplomaticLines.removeChild(this.$refs.diplomaticLines.lastChild);
            }
        },

        getAPITextAnnotationBody(annotation, offsets) {
            var body = this.getAPIAnnotationBody(annotation);
            let total = 0;
            for(let i=0; i<this.$refs.diploLineComponents.length; i++) {
                let currentLine = this.$refs.diploLineComponents[i];
                let content = currentLine.getEl().textContent;
                if (!body.start_line && total+content.length > offsets.start) {
                    body.start_line = currentLine.line.pk;
                    body.start_offset = offsets.start - total;
                }
                if (!body.end_line && total+content.length >= offsets.end) {
                    body.end_line = currentLine.line.pk;
                    body.end_offset = offsets.end - total;
                }
                if(body.start_line && body.end_line) break;
                total += content.length;
            }
            return body;
        },

        makeTaxonomiesStyles() {
            var hexToRGB = function(hex) {
                var result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
                return result
                    ? [
                        parseInt(result[1], 16), parseInt(result[2], 16), parseInt(result[3], 16)
                    ]
                    : null;
            };

            let style = document.createElement("style");
            style.type = "text/css";
            style.id = "anno-text-taxonomies-styles";
            document.getElementsByTagName("head")[0].appendChild(style);
            // dynamically creates a class for each taxonomies
            this.annotationTaxonomies.text.forEach((taxo) => {
                let className = "anno-" + taxo.pk;
                if (taxo.marker_type == "Background Color") {
                    let rgb = hexToRGB(taxo.marker_detail);
                    style.innerHTML += "\n." + className + " {background-color: rgba("+rgb[0]+","+rgb[1]+","+rgb[2]+", 0.2); border-bottom: 2px solid "+taxo.marker_detail+";}";
                } else if (taxo.marker_type == "Text Color") {
                    style.innerHTML += "\n." + className + " {background-color: white; border-bottom: none; color: " + taxo.marker_detail + ";}";
                } else if (taxo.marker_type == "Bold") {
                    style.innerHTML += "\n." + className + " {background-color: white; border-bottom: none; font-weight: bold;}";
                } else if (taxo.marker_type == "Italic") {
                    style.innerHTML += "\n." + className + " {background-color: white; border-bottom: none; font-style: italic;}";
                }
            });
        },

        async loadAnnotations() {
            if (
                this.legacyModeEnabled &&
                document.getElementById("anno-text-taxonomies-styles") == null
            )
                this.makeTaxonomiesStyles();

            let annos = await this.fetchTextAnnotations();
            annos.forEach(function(annotation) {
                let data = annotation.as_w3c;
                data.id = annotation.pk;
                data.taxonomy = this.annotationTaxonomies.text.find(
                    (e) => e.pk == annotation.taxonomy
                );
                this.anno.addAnnotation(data);
            }.bind(this));
        },
        textAnnoFormatter (annotation) {
            const anno = annotation.underlying;
            if (this.legacyModeEnabled) {
                const className = "anno-" + (
                    anno.taxonomy != undefined && anno.taxonomy.pk || this.currentTaxonomy.pk
                );
                return className;
            } else {
                const color = anno?.taxonomy?.marker_detail || this.currentTaxonomy.marker_detail;
                /**
                 *  TODO: all annotations get underlines
                 *  text-decoration: underline 3px ${color};
                 *  text-underline-position: under;
                 */
                let style = `
                    background-color: transparent;
                    border-bottom: none;
                `;
                switch (anno?.taxonomy?.marker_type || this.currentTaxonomy.marker_type) {
                    case "Background Color":
                        style = `${style} background-color: ${color}33;`;
                        // TODO: remove below when doubling bug is fixed
                        style = `${style} border-bottom: 2px solid ${color};`;
                        break;
                    case "Text Color":
                        style = `${style} color: ${color};`
                        break;
                    case "Bold":
                        style = `${style} font-weight: bold;`;
                        break;
                    case "Italic":
                        style = `${style} font-style: italic;`;
                        break;
                    default:
                        break;
                }
                return { style };
            }
        },
        initAnnotations() {
            this.anno = new Recogito({
                content: this.$refs.contentContainer,
                allowEmpty: true,
                readOnly: true,
                widgets: [],
                disableEditor: false,
                formatter: this.textAnnoFormatter.bind(this),
            });

            this.isEditorOpen = false;
            const editorOpenObserver = function(mutationsList) {
                // let's hope for no race condition with the contenteditable focusin/out...
                for (let mutation of mutationsList) {
                    if (mutation.addedNodes.length) {
                        this.isEditorOpen = true;
                        this.setBlockShortcuts(true);
                    } else if (mutation.removedNodes.length) {
                        this.isEditorOpen = false;
                        this.setBlockShortcuts(false);
                    }
                }
            }.bind(this);
            const editorObserver = new MutationObserver(editorOpenObserver);
            editorObserver.observe(this.anno._appContainerEl, {childList: true});

            this.anno.on("createAnnotation", async function(annotation) {
                annotation.taxonomy = this.currentTaxonomy;
                let offsets = annotation.target.selector.find(
                    (e) => e.type == "TextPositionSelector"
                );
                let body = this.getAPITextAnnotationBody(annotation, offsets);
                body.transcription = this.selectedTranscription;
                const newAnno = await this.createTextAnnotation(body);
                // updates actual object (annotation is just a copy)
                annotation.id = newAnno.pk;
                this.anno.addAnnotation(annotation);
            }.bind(this));

            this.anno.on("updateAnnotation", function(annotation) {
                let offsets = annotation.target.selector;
                let body = this.getAPITextAnnotationBody(annotation, offsets);
                body.id = annotation.id;
                this.updateTextAnnotation(body);
            }.bind(this));

            this.anno.on("selectAnnotation", function(annotation) {
                if (annotation.taxonomy && this.currentTaxonomy != annotation.taxonomy) {
                    this.toggleTaxonomy(annotation.taxonomy);
                }
            }.bind(this));

            this.anno.on("deleteAnnotation", function(annotation) {
                this.deleteTextAnnotation(annotation.id);
            }.bind(this));
        },

        toggleSort() {
            if (this.$refs.diplomaticLines.contentEditable === "true") {
                this.$refs.diplomaticLines.contentEditable = "false";
                this.sortable.option("disabled", false);
                this.isSortModeEnabled = true;
                if (this.$refs.sortMode) {
                    this.$refs.sortMode.classList.remove("btn-info");
                    this.$refs.sortMode.classList.add("btn-success");
                }
            } else {
                this.$refs.diplomaticLines.contentEditable = "true";
                this.sortable.option("disabled", true);
                this.isSortModeEnabled = false;
                if (this.$refs.sortMode) {
                    this.$refs.sortMode.classList.remove("btn-success");
                    this.$refs.sortMode.classList.add("btn-info");
                }
            }
        },

        recalculateAnnotationSelectors() {
            for (let anno of this.anno.getAnnotations()) {
                let annoEls = document.querySelectorAll('.r6o-annotation[data-id="'+anno.id+'"]');

                if (annoEls === null) {
                    this.deleteTextAnnotation(anno.id);
                }

                let range = document.createRange();
                range.setStart(annoEls[0], 0);
                range.setEnd(annoEls[annoEls.length-1], 1);
                let rangeBefore = document.createRange();
                rangeBefore.setStart(this.$refs.contentContainer, 0);
                rangeBefore.setEnd(range.startContainer, range.startOffset);
                let quote = range.toString();
                let oldStart = anno.target.selector.start;
                let oldEnd = anno.target.selector.end;
                let start = rangeBefore.toString().length;
                let end = start + quote.length;
                anno.target.selector = {
                    type: "TextPositionSelector",
                    start: start,
                    end: end
                };

                let body = this.getAPITextAnnotationBody(anno, anno.target.selector);
                body.id = anno.id;
                if (oldStart != start || oldEnd != end) {
                    this.updateTextAnnotation(body);
                }
            }
        },

        changed() {
            this.$refs.saveNotif.classList.remove("hide");
            this.debouncedSave();
        },

        appendLine(pos) {
            let div = document.createElement("div");
            div.appendChild(document.createElement("br"));
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
            // Removes any rogue 'br' added by the browser
            const diploLines = this.$refs.diplomaticLines;
            diploLines.querySelectorAll(":scope > br").forEach((n) => n.remove());

            // Add lines until we have enough of them
            while (diploLines.childElementCount < this.allLines.length) {
                this.appendLine();
            }

            // need to add/remove danger indicators
            for (let i=0; i<diploLines.childElementCount; i++) {
                let line = diploLines.querySelector(`div:nth-child(${parseInt(i+1)})`);
                if (line === null) {
                    line.remove();
                    continue;
                }

                if (i<this.allLines.length) {
                    line.classList.remove("alert-danger");
                    line.setAttribute("title", "");
                } else if (i>=this.allLines.length) {
                    if (line.textContent == "") { // just remove empty lines
                        line.remove();
                    } else  {
                        line.classList.add("alert-danger");
                        line.setAttribute("title", "More lines than there is in the segmentation!");
                    }
                }
            }
        },

        startEdit() {
            this.setBlockShortcuts(true);
        },

        stopEdit() {
            if (this.isEditorOpen !== true) {
                this.setBlockShortcuts(false);
            }
            this.constrainLineNumber();
            this.save();
        },

        onDraggingEnd(ev) {
            /*
               Finish dragging lines, save new positions
             */
            if(ev.newIndicies.length == 0 && ev.newIndex != ev.oldIndex) {
                let diploLine = this.$refs.diploLineComponents.find(
                    (dl)=>dl.line.order==ev.oldIndex
                );
                this.movedLines.push({
                    "pk": diploLine.line.pk,
                    "order": ev.newIndex
                });
            } else {
                for(let i=0; i< ev.newIndicies.length; i++) {

                    let diploLine = this.$refs.diploLineComponents.find(
                        (dl)=>dl.line.order==ev.oldIndicies[i].index
                    );
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
                    await this.$store.dispatch("lines/move", this.movedLines)
                    this.movedLines = []
                } catch (err) {
                    console.log("couldn't recalculate order of line", err)
                }
            }
        },

        save() {
            /*
               if some lines are modified add them to updatedlines,
               new lines add them to createdLines then save
            */
            this.$refs.saveNotif.classList.add("hide");
            this.addToList();
            var updated = this.bulkUpdate();
            this.bulkCreate();
            updated.then(function(value) {
                if (value > 0) this.recalculateAnnotationSelectors();
            }.bind(this));

            // check if some annotations were completely deleted by the erasing the text
            for (let annotation of this.allTextAnnotations) {
                let annoEl = document.querySelector('.r6o-annotation[data-id="'+annotation.pk+'"]');
                if (annoEl === null) this.deleteTextAnnotation(annotation.pk);
            }
        },

        focusNextLine(sel, line) {
            if (line.nextSibling) {
                let range = document.createRange();
                range.setStart(line.nextSibling, 0);
                range.collapse(false);
                sel.removeAllRanges();
                const container = this.$refs.contentContainer;

                if (line.nextSibling.offsetTop > (container.scrollTop + container.clientHeight)) {
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
            if (ev.key == "ArrowDown" && !ev.shiftKey) {
                let sel = window.getSelection();
                let div = sel.anchorNode.nodeType === Node.TEXT_NODE
                    ? sel.anchorNode.parentElement
                    : sel.anchorNode;
                this.focusNextLine(sel, div);
                ev.preventDefault();
            } else if (ev.key == "ArrowUp" && !ev.shiftKey) {
                let sel = window.getSelection();
                let div = sel.anchorNode.nodeType === Node.TEXT_NODE
                    ? sel.anchorNode.parentElement
                    : sel.anchorNode;
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

            let pastedData;
            if (e && e.clipboardData && e.clipboardData.getData) {
                pastedData = e.clipboardData.getData("text/plain");

                var cursor = sel.getRangeAt(0);  // specific position or range
                // for a range, delete content to clean data and to get resulting
                // specific cursor position from it:
                cursor.deleteContents();
                // if selection is done on several lines, cursor caret be placed between 2 divs

                // after deleting (for an range),
                // check if resulting cursor is in or off a line div or some errors will occur!:
                let parentEl = sel.getRangeAt(0).commonAncestorContainer;
                if (parentEl.nodeType != 1) {
                    // for several different lines, commonAncestorContainer does not exist
                    parentEl = parentEl.parentNode;
                }

                let pasted_data_split = pastedData.split("\n");
                let refNode = parentEl;

                let textBeforeCursor = "";
                let textAfterCursor = "";

                // nodes which will be placed before and after the targetnode where text is
                // pasted (new node or current node)
                let prevSibling;
                let nextSibling;

                if(parentEl.id == "diplomatic-lines"){
                    // if parent node IS the main diplomatic panel div = cursor is offline
                    // occurs when a selection is made on several lines or all is selected

                    //we create a between node:
                    refNode = document.createElement("div");
                    refNode.textContent = "";

                    // paste text on the selection (cursor position or range):
                    cursor.insertNode(refNode);

                    // set caret position/place the cursor into the new node:
                    cursor.setStart(refNode,0);
                    cursor.setEnd(refNode,0);

                    // in this case, contents before and after selection will belong to near
                    // siblings
                    if(refNode.previousSibling != null){
                        prevSibling = refNode.previousSibling;
                    }
                    if(refNode.nextSibling != null){
                        nextSibling = refNode.nextSibling;
                    }
                }

                //  get current cursor position within the line div tag
                let caretPos = cursor.endOffset;
                //  4   //  nombre de caractères du début jusqu'à la position du curseur

                // store previous and next text in the line to it / for a selection within on line:
                textBeforeCursor = refNode.textContent.substring(0, caretPos);
                textAfterCursor = refNode.textContent.substring(
                    caretPos, refNode.textContent.length
                );

                // for a selection between several lines, contents before and after will be the
                // contents of siblings
                // to avoid create new lines before and after, fusion of sibling contents to the
                // current node and removing it
                if(typeof(prevSibling) != "undefined"){
                    textBeforeCursor = prevSibling.textContent;
                    prevSibling.parentNode.removeChild(prevSibling);
                }
                if(typeof(nextSibling) != "undefined"){
                    textAfterCursor = nextSibling.textContent;
                    nextSibling.parentNode.removeChild(nextSibling);
                }
                // will set the new cursor position
                let endPos = 0;
                // last impacted node for a copy-paste (for several lines)
                let lastTargetNode = refNode;

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

                    for(var k=1; k < nextNodesContents.length; k++)
                    {
                        //  for any other line, we add a div and set this content
                        var prevLineDiv = document.createElement("div");
                        prevLineDiv.textContent = nextNodesContents[k];
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

            // Stop the data from actually being pasted
            //  without it will paste the native copied text after "content"
            e.stopPropagation();
            e.preventDefault();
        },

        showOverlay(ev) {
            let target = ev.target.closest("div");
            let index = Array.prototype.indexOf.call(target.parentNode.children, target);
            if (index > -1 && index < this.$refs.diploLineComponents.length) {
                let diploLine = this.$refs.diploLineComponents.find((dl)=>dl.line.order==index);
                if (diploLine) diploLine.showOverlay();
            } else {
                this.hideOverlay();
            }
        },

        hideOverlay() {
            if (this.$refs.diploLineComponents.length) {
                this.$refs.diploLineComponents[0].hideOverlay();
            }
        },

        async bulkUpdate() {
            var toUpdate = this.updatedLines.length;
            if(toUpdate) {
                await this.$store.dispatch("transcriptions/bulkUpdate", this.updatedLines);
                this.updatedLines = [];
            }
            return toUpdate;
        },

        async bulkCreate() {
            if(this.createdLines.length) {
                await this.$store.dispatch("transcriptions/bulkCreate", this.createdLines);
                this.createdLines = [];
            }
        },

        addToList() {
            /*
               parse all lines if the content changed, add it to updated lines
             */
            for(let i=0; i<this.$refs.diploLineComponents.length; i++) {
                let currentLine = this.$refs.diploLineComponents[i];
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
            let elt = this.updatedLines.find((l) => l.pk === lt.pk);
            if(elt == undefined) {
                this.updatedLines.push(lt);
            } else {
                elt.content = lt.content;
                elt.version_updated_at = lt.version_updated_at;
            }
        },

        setHeight() {
            const minHeight = Math.round(this.$store.state.parts.image.size[1] * this.ratio);
            this.$refs.contentContainer.style.minHeight =  `${minHeight}px`;
        },

        updateView() {
            if (this.legacyModeEnabled) {
                this.setHeight();
            }
        },

        setThisAnnoTaxonomy(taxo) {
            this.setTextAnnoTaxonomy(taxo);
        },

        setTextAnnoTaxonomy(taxo) {
            var colorFormatter = function() {
                // todo: find a way to pass the marker_detail..
                return "colored-text";
            };
            var boldFormatter = function() {
                return "strong";
            };
            var italicFormatter = function() {
                return "italic";
            };
            let marker_map = {
                "Background Color": null,
                "Text Color": colorFormatter,
                "Bold" : boldFormatter,
                "Italic": italicFormatter
            };
            this.anno.formatter = marker_map[taxo.marker_type];
            this.setAnnoTaxonomy(taxo);
        },

        activateVK(div) {
            div.contentEditable = "true";
            this.$refs.diplomaticLines.contentEditable = "false";
            // eslint-disable-next-line no-undef
            enableVirtualKeyboard(div);
        },

        deactivateVK(div) {
            div.removeAttribute("contentEditable");
            this.$refs.diplomaticLines.contentEditable = "true";
            div.onfocus = (e) => { e.preventDefault() };
        },

        toggleVK() {
            this.isVKEnabled = !this.isVKEnabled;
            let vks = this.enabledVKs;
            if (this.isVKEnabled) {
                vks.push(this.documentId);
                this.$store.commit("document/setEnabledVKs", vks);
                // eslint-disable-next-line no-undef
                userProfile.set("VK-enabled", vks);
                this.$refs.diplomaticLines.childNodes.forEach((c) => {
                    this.activateVK(c);
                });
                if (!this.legacyModeEnabled && this.isSortModeEnabled) {
                    this.$refs.diplomaticLines.contentEditable = "true";
                    this.sortable.option("disabled", true);
                    this.isSortModeEnabled = false;
                }
            } else {
                // Make sure we save changes made before we remove the VK
                vks.splice(vks.indexOf(this.documentId), 1);
                this.$store.commit("document/setEnabledVKs", vks);
                // eslint-disable-next-line no-undef
                userProfile.set("VK-enabled", vks);
                this.$refs.diplomaticLines.childNodes.forEach((c) => {
                    this.deactivateVK(c);
                });
            }
        },

        /**
         * New UI: ensure max height of DiploPanel takes height of annotation toolbar
         * into account.
         */
        recalculatePanelHeight() {
            const toolbarHeight = this.$refs.annotationToolbar.clientHeight;
            const newHeight = `calc(100vh - 180px - ${toolbarHeight}px)`;
            this.$refs.contentContainer.style.setProperty("min-height", newHeight);
            this.$refs.contentContainer.style.setProperty("max-height", newHeight);
        },
    }
}
</script>
