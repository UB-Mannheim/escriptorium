<template>
    <div
        id="trans-modal"
        ref="transModal"
        :class="{ modal: true, ['escr-line-modal']: !legacyModeEnabled }"
        role="dialog"
    >
        <div
            class="modal-dialog modal-xl"
            role="document"
        >
            <div class="modal-content">
                <div
                    v-if="legacyModeEnabled"
                    class="modal-header"
                >
                    <button
                        v-if="readDirection == 'rtl'"
                        id="next-btn"
                        type="button"
                        title="Next (up arrow)"
                        class="btn btn-sm mr-1 btn-secondary"
                        @click="editLine('next')"
                    >
                        <i class="fas fa-arrow-circle-left" />
                    </button>
                    <button
                        v-else
                        id="prev-btn"
                        type="button"
                        title="Previous (up arrow)"
                        class="btn btn-sm mr-1 btn-secondary"
                        @click="editLine('previous')"
                    >
                        <i class="fas fa-arrow-circle-left" />
                    </button>

                    <button
                        v-if="readDirection == 'rtl'"
                        id="prev-btn"
                        type="button"
                        title="Previous (down arrow)"
                        class="btn btn-sm mr-1 btn-secondary"
                        @click="editLine('previous')"
                    >
                        <i class="fas fa-arrow-circle-right" />
                    </button>
                    <button
                        v-else
                        id="next-btn"
                        type="button"
                        title="Next (down arrow)"
                        class="btn btn-sm mr-1 btn-secondary"
                        @click="editLine('next')"
                    >
                        <i class="fas fa-arrow-circle-right" />
                    </button>
                    <button
                        class="btn btn-sm ml-2 mr-1"
                        :class="{'btn-info': isVKEnabled, 'btn-outline-info': !isVKEnabled}"
                        title="Toggle Virtual Keyboard for this document."
                        @click="toggleVK"
                    >
                        <i class="fas fa-keyboard" />
                    </button>

                    <h5
                        id="modal-label"
                        class="modal-title ml-3"
                    >
                        Line #{{ line.order + 1 }}
                    </h5>

                    <button
                        type="button"
                        class="close"
                        aria-label="Close"
                        @click="close"
                    >
                        <span aria-hidden="true">&times;</span>
                    </button>
                </div>
                <div
                    v-else
                    class="modal-header escr-line-modal-header"
                >
                    <h2>Line #{{ line.order + 1 }}</h2>
                    <EscrButton
                        color="text"
                        :on-click="() => editLine(readDirection === 'rtl' ? 'next' : 'previous')"
                        size="small"
                    >
                        <template #button-icon>
                            <ArrowCircleLeftIcon />
                        </template>
                    </EscrButton>
                    <EscrButton
                        color="text"
                        :on-click="() => editLine(readDirection === 'rtl' ? 'previous' : 'next')"
                        size="small"
                    >
                        <template #button-icon>
                            <ArrowCircleRightIcon />
                        </template>
                    </EscrButton>
                    <div class="new-section with-separator">
                        <ToggleButton
                            class="escr-vk-toggle"
                            size="small"
                            :checked="isVKEnabled"
                            :on-change="toggleVK"
                        >
                            <template #button-icon>
                                <KeyboardIcon />
                            </template>
                        </ToggleButton>
                    </div>
                    <div class="escr-line-modal-right">
                        <EscrButton
                            color="text"
                            :on-click="() => close()"
                            size="small"
                        >
                            <template #button-icon>
                                <XIcon />
                            </template>
                        </EscrButton>
                    </div>
                </div>
                <div :class="'modal-body ' + defaultTextDirection">
                    <p
                        v-if="line.mask == null"
                        dir="ltr"
                        class="text-warning"
                    >
                        No mask found for the line, preview unavailable!
                        <span v-if="legacyModeEnabled">
                            Calculate masks by hitting the green thumbs up button in the
                            segmentation panel.
                        </span>
                    </p>
                    <div
                        id="modal-img-container"
                        ref="modalImgContainer"
                        width="80%"
                    >
                        <img
                            id="line-img"
                            :src="modalImgSrc"
                            draggable="false"
                            selectable="false"
                        >
                        <div class="overlay">
                            <svg
                                width="100%"
                                height="100%"
                            >
                                <defs>
                                    <mask id="modal-overlay">
                                        <rect
                                            width="100%"
                                            height="100%"
                                            fill="white"
                                        />
                                        <polygon points="" />
                                    </mask>
                                </defs>
                                <rect
                                    fill="grey"
                                    opacity="0.5"
                                    width="100%"
                                    height="100%"
                                    mask="url(#modal-overlay)"
                                />
                            </svg>
                        </div>
                    </div>

                    <!-- TODO: Refactor to not use refs (use vuex store or component data) -->
                    <div
                        id="trans-input-container"
                        ref="transInputContainer"
                    >
                        <input
                            v-if="mainTextDirection != 'ttb'"
                            id="trans-input"
                            ref="transInput"
                            v-model.lazy="localTranscription"
                            name="content"
                            class="form-control mb-2 display-virtual-keyboard"
                            autocomplete="off"
                            autofocus
                            @keyup.down="editLine('next')"
                            @keyup.up="editLine('previous')"
                            @keyup.enter="editLine('next')"
                        >
                        <!--Hidden input for ttb text: -->
                        <input
                            v-else
                            id="trans-input"
                            ref="transInput"
                            v-model.lazy="localTranscription"
                            name="content"
                            type="hidden"
                            autocomplete="off"
                        >
                        <!-- in this case, input field is replaced by: -->
                        <div
                            v-if="mainTextDirection == 'ttb'"
                            id="textInputWrapper"
                        >
                            <div
                                id="textInputBorderWrapper"
                                class="form-control mb-2"
                            >
                                <div
                                    id="vertical_text_input"
                                    contenteditable="true"
                                    class="display-virtual-keyboard"
                                    @blur="localTranscription = $event.target.textContent"
                                    @keyup="recomputeInputCharsScaleY()"
                                    @keyup.right="editLine('next')"
                                    @keyup.left="editLine('previous')"
                                    @keyup.enter="cleanHTMLTags();recomputeInputCharsScaleY();editLine('next')"
                                    v-html="localTranscription"
                                />
                            </div>
                        </div>

                        <small
                            v-if="line.currentTrans && line.currentTrans.version_updated_at"
                            class="form-text text-muted"
                        >
                            <span>by {{ line.currentTrans.version_author }} ({{ line.currentTrans.version_source }})</span>
                            <span>on {{ momentDate }}</span>
                        </small>
                    </div>

                    <hr v-if="!legacyModeEnabled">

                    <!-- transcription comparison -->
                    <details
                        v-if="!legacyModeEnabled"
                        class="escr-compare"
                    >
                        <summary dir="ltr">
                            <span>Transcription comparison</span>
                            <TranscriptionSelector />
                        </summary>
                        <div
                            v-if="comparedTranscriptions.length"
                            id="comparison"
                            class="compare-show"
                        >
                            <div
                                class="d-table"
                            >
                                <div
                                    v-for="trans in otherTranscriptions"
                                    :key="'TrC' + trans.pk"
                                    class="d-table-row"
                                >
                                    <div
                                        class="d-table-cell col"
                                        v-html="comparedContent(trans.content)"
                                    />
                                    <div
                                        class="d-table-cell text-muted text-nowrap col"
                                        title="Transcription name"
                                    >
                                        <small>
                                            {{ trans.name }}
                                            <span
                                                v-if="trans.pk == selectedTranscription"
                                            >
                                                (current)
                                            </span>
                                        </small>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <span
                            v-else
                            class="escr-no-content"
                        >
                            No transcriptions selected
                        </span>
                    </details>
                    <div
                        v-else-if="comparedTranscriptions.length"
                        class="card history-block mt-2"
                    >
                        <div class="card-header">
                            <a
                                href="#"
                                class="card-toggle collapsed"
                                data-toggle="collapse"
                                data-target=".compare-show"
                            >
                                <span>Toggle transcription comparison</span>
                            </a>

                            <button
                                title="Help."
                                data-toggle="collapse"
                                data-target="#compare-help"
                                class="btn btn-info fas fa-question help nav-item ml-2"
                            />
                            <div
                                id="compare-help"
                                class="alert alert-primary help-text collapse"
                            >
                                <HelpCompareTranscriptions />
                            </div>
                        </div>
                        <div
                            id="comparison"
                            class="compare-show card-body collapse"
                        >
                            <div class="d-table">
                                <div
                                    v-for="trans in otherTranscriptions"
                                    :key="'TrC' + trans.pk"
                                    class="d-table-row"
                                >
                                    <div
                                        class="d-table-cell col"
                                        v-html="comparedContent(trans.content)"
                                    />
                                    <div
                                        class="d-table-cell text-muted text-nowrap col"
                                        title="Transcription name"
                                    >
                                        <small>
                                            {{ trans.name }}
                                            <span v-if="trans.pk == selectedTranscription">(current)</span></small>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <hr v-if="!legacyModeEnabled">

                    <!-- versioning/history -->
                    <details v-if="!legacyModeEnabled">
                        <summary dir="ltr">
                            <span>Transcription history</span>
                        </summary>
                        <div
                            v-if="line.currentTrans &&
                                line.currentTrans.versions &&
                                line.currentTrans.versions.length"
                            id="history"
                            class="history-show"
                        >
                            <div class="d-table">
                                <LineVersion
                                    v-for="(version, index) in line.currentTrans.versions"
                                    :key="version.revision"
                                    :previous="line.currentTrans.versions[index+1]"
                                    :version="version"
                                    :line="line"
                                    :legacy-mode-enabled="legacyModeEnabled"
                                />
                            </div>
                        </div>
                        <span
                            v-else
                            class="escr-no-content"
                        >
                            No history to display
                        </span>
                    </details>
                    <div
                        v-else-if="line.currentTrans &&
                            line.currentTrans.versions &&
                            line.currentTrans.versions.length"
                        class="card history-block mt-2"
                    >
                        <div class="card-header">
                            <a
                                href="#"
                                class="card-toggle collapsed"
                                data-toggle="collapse"
                                data-target=".history-show"
                            >
                                <span>Toggle history</span>
                            </a>
                            <button
                                title="Help."
                                data-toggle="collapse"
                                data-target="#versions-help"
                                class="btn btn-info fas fa-question help nav-item ml-2 collapsed"
                            />
                            <div
                                id="versions-help"
                                class="alert alert-primary help-text collapse"
                            >
                                <HelpVersions />
                            </div>
                        </div>
                        <div
                            id="history"
                            class="history-show card-body collapse"
                        >
                            <div class="d-table">
                                <LineVersion
                                    v-for="(version, index) in line.currentTrans.versions"
                                    v-if="line.currentTrans && line.currentTrans.versions"
                                    :key="version.revision"
                                    :previous="line.currentTrans.versions[index+1]"
                                    :version="version"
                                    :line="line"
                                    :legacy-mode-enabled="legacyModeEnabled"
                                />
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import { mapState } from "vuex";
import ArrowCircleLeftIcon from "./Icons/ArrowCircleLeftIcon/ArrowCircleLeftIcon.vue";
import ArrowCircleRightIcon from "./Icons/ArrowCircleRightIcon/ArrowCircleRightIcon.vue";
import EscrButton from "./Button/Button.vue";
import KeyboardIcon from "./Icons/KeyboardIcon/KeyboardIcon.vue";
import LineVersion from "./LineVersion.vue";
import HelpVersions from "./HelpVersions.vue";
import HelpCompareTranscriptions from "./HelpCompareTranscriptions.vue";
import ToggleButton from "./ToggleButton/ToggleButton.vue";
import TranscriptionSelector from "./TranscriptionSelector/TranscriptionSelector.vue";
import XIcon from "./Icons/XIcon/XIcon.vue";
import "./TranscriptionModal.css";

export default Vue.extend({
    components: {
        ArrowCircleLeftIcon,
        ArrowCircleRightIcon,
        EscrButton,
        KeyboardIcon,
        LineVersion,
        HelpVersions,
        HelpCompareTranscriptions,
        ToggleButton,
        TranscriptionSelector,
        XIcon,
    },
    props: {
        /**
         * Whether or not legacy mode is enabled by the user.
         */
        legacyModeEnabled: {
            type: Boolean,
            required: true,
        },
    },
    data() {
        return {
            isVKEnabled: false
        }
    },
    computed: {
        ...mapState({
            allTranscriptions: (state) => state.transcriptions.all,
            comparedTranscriptions: (state) => state.transcriptions.comparedTranscriptions,
            defaultTextDirection: (state) => state.document.defaultTextDirection,
            documentId: (state) => state.document.id,
            enabledVKs: (state) => state.document.enabledVKs,
            image: (state) => state.parts.image,
            line: (state) => state.lines.editedLine,
            mainTextDirection: (state) => state.document.mainTextDirection,
            readDirection: (state) => state.document.readDirection,
            selectedTranscription: (state) => state.transcriptions.selectedTranscription,
        }),
        momentDate() {
            return moment.tz(this.line.currentTrans.version_updated_at, this.timeZone);
        },
        modalImgSrc() {
            if (this.image.uri.endsWith(".tif") ||
                 this.image.uri.endsWith(".tiff")) {
                // can't display tifs so fallback to large thumbnail
                return this.image.thumbnails.large;
            } else {
                return this.image.uri;
            }
        },
        otherTranscriptions() {
            let a = Object
                .keys(this.line.transcriptions)
                .filter((pk)=>this.comparedTranscriptions
                    .includes(parseInt(pk)))
                .map((pk)=>{ return {
                    pk: pk,
                    name: this.allTranscriptions.find((e)=>e.pk==pk).name,
                    content: this.line.transcriptions[pk].content
                }; });
            return a;
        },
        localTranscription: {
            get: function() {
                return this.line.currentTrans && this.line.currentTrans.content || "";
            },
            set: async function(newValue) {
                let oldValue = this.line.currentTrans.content;
                if (this.$refs.transInput.value != newValue) {
                    // Note: better way to do that?
                    this.$refs.transInput.value = newValue;
                    this.computeStyles();
                }

                if (oldValue != newValue) {
                    await this.$store.dispatch("transcriptions/updateLineTranscriptionVersion", { line: this.line, content: newValue });
                }
            }
        },
    },
    watch: {
        line() {
            this.computeStyles();
        },
        enabledVKs() {
            this.isVKEnabled = this.enabledVKs.indexOf(this.documentId) != -1 || false;
        }
    },
    created() {
        $(document).on("hide.bs.modal", "#trans-modal", function(ev) {
            if (this.localTranscription != this.$refs.transInput.value
                && !confirm("You have unsaved data, are you sure you want to close the modal?")) {
                return false;
            }

            if (this.isVKEnabled) {
                for (const input of [...document.getElementsByClassName("display-virtual-keyboard")])
                    input.blur();
            }
            this.$store.dispatch("lines/toggleLineEdition", null);

            // make sure that typing in the input does not trigger keyboard shortcuts
            this.$store.commit("document/setBlockShortcuts", false);
        }.bind(this));

        $(document).on("show.bs.modal", "#trans-modal", function(ev) {
            this.$store.commit("document/setBlockShortcuts", true);
        }.bind(this));

        this.timeZone = moment.tz.guess();
    },
    deactivated() {
        // make sure the modal is cleanly closed when the panel is hidden
        $(this.$refs.transModal).modal("hide");
    },
    destroyed() {
        // unbind all events to avoid duplicating them
        $(document).off("hide.bs.modal");
        $(document).off("show.bs.modal");
    },
    mounted() {
        $(this.$refs.transModal).modal({show: true});
        $(this.$refs.transModal).draggable({handle: ".modal-header"});
        $(this.$refs.transModal).resizable();
        this.computeStyles();
        let modele = this;

        let input = this.$refs.transInput;

        // no need to make focus on hidden input with a ttb text
        if(this.mainTextDirection != "ttb"){
            input.focus();
        }else{  // avoid some br or other html tag for a copied text on an editable input div (vertical_text_input):
            //
            document.getElementById("vertical_text_input").addEventListener("paste", function(e) {

                // cancel paste to treat its content before inserting it
                e.preventDefault();

                // get text representation of clipboard
                var text = (e.originalEvent || e).clipboardData.getData("text/plain");
                this.innerHTML = text;
                modele.recomputeInputCharsScaleY();

            }, false);
        }

        this.isVKEnabled = this.enabledVKs.indexOf(this.documentId) != -1 || false;
        if (this.isVKEnabled)
            for (const input of [...document.getElementsByClassName("display-virtual-keyboard")])
                enableVirtualKeyboard(input);
    },
    methods: {
        close() {
            $(this.$refs.transModal).modal("hide");
        },

        editLine(direction) {
            // making sure the line is saved (it isn't in case of shortcut usage)
            this.localTranscription = this.$refs.transInput.value;
            this.$store.dispatch("lines/editLine", direction);
        },

        cleanHTMLTags(){
            document.getElementById("vertical_text_input").innerHTML = document.getElementById("vertical_text_input").textContent;
        },
        recomputeInputCharsScaleY(){

            let inputHeight = document.getElementById("vertical_text_input").clientHeight;
            let wrapperHeight = document.getElementById("textInputBorderWrapper").clientHeight;
            let textScaleY = wrapperHeight / (inputHeight + 10);

            // to avoid input text outside the border box:
            if(inputHeight > wrapperHeight)
                document.getElementById("vertical_text_input").style.transform = "scaleY("+textScaleY+")";
        },
        comparedContent(content) {
            if (!this.line.currentTrans) return;
            let diff = Diff.diffChars(this.line.currentTrans.content, content);
            return diff.map(function(part){
                if (part.removed) {
                    return '<span class="cmp-del">'+part.value+"</span>";
                } else if (part.added) {
                    return '<span class="cmp-add">'+part.value+"</span>";
                } else {
                    return part.value;
                }
            }.bind(this)).join("");
        },

        getLineAngle() {
            let p1, p2;
            if (this.line.baseline) {
                p1 = this.line.baseline[0];
                p2 = this.line.baseline[this.line.baseline.length-1];
            } else {
                // fake baseline from left most to right most points in mask
                p1 = this.line.mask.reduce((minPt, curPt) => (curPt[0] < minPt[0]) ? curPt : minPt);
                p2 = this.line.mask.reduce((maxPt, curPt) => (curPt[0] > maxPt[0]) ? curPt : maxPt);
            }

            return Math.atan2(p2[1] - p1[1], p2[0] - p1[0]) * 180 / Math.PI;
        },

        getRotatedLineBBox() {
            // create temporary polygon to calculate the line bounding box
            if (this.line.mask) {
                var maskPoints = this.line.mask.map(
                    (pt) => Math.round(pt[0])+ ","+
                        Math.round(pt[1])).join(" ");
            } else {
                // TODO
            }
            let svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
            let tmppoly = document.createElementNS("http://www.w3.org/2000/svg",
                "polygon");
            tmppoly.setAttributeNS(null, "points", maskPoints);
            tmppoly.setAttributeNS(null, "fill", "red");

            // calculate rotation needed to get the line horizontal
            let target_angle = 0;  // all lines should be topologically ltr
            if(this.mainTextDirection == "ttb") // add a 90 angle for vertical texts
                target_angle = 90;
            let angle = target_angle - this.getLineAngle();

            // apply it to the polygon and get the resulting bbox
            let transformOrigin =  this.image.size[0]/2+"px "+this.image.size[1]/2+"px";
            tmppoly.style.transformOrigin = transformOrigin;
            tmppoly.style.transform = "rotate("+angle+"deg)";
            svg.appendChild(tmppoly);
            document.body.appendChild(svg);
            let bbox = tmppoly.getBoundingClientRect();
            let width = bbox.width;
            let height = bbox.height
            let top = bbox.top - svg.getBoundingClientRect().top;
            let left = bbox.left - svg.getBoundingClientRect().left;
            document.body.removeChild(svg); // done its job
            return {width: width, height: height, top: top, left: left, angle: angle};
        },

        computeImgStyles(bbox, ratio, lineHeight, hContext) {
            let modalImgContainer = this.$refs.modalImgContainer;
            let img = modalImgContainer.querySelector("img#line-img");

            let context = hContext*lineHeight;
            let visuHeight = lineHeight + 2*context;

            if(this.mainTextDirection != "ttb"){
                modalImgContainer.style.height = visuHeight+"px";
            }else{
                modalImgContainer.style.width = visuHeight+"px";
                modalImgContainer.style.display = "inline-block";
                modalImgContainer.style.verticalAlign = "top";
            }
            let top = -(bbox.top*ratio - context);
            let left = -(bbox.left*ratio - context);

            // if text direction is rtl and the line doesn't take all the space,
            // align it to the right
            if (modalImgContainer.clientWidth - 2*context > bbox.width*ratio
                && this.defaultTextDirection == "rtl") {
                left += modalImgContainer.clientWidth - 2*context - bbox.width*ratio;
            }

            // modalImgContainer.style.transform = 'scale('+ratio+')';

            let imgWidth = this.image.size[0]*ratio +"px";
            let transformOrigin =  this.image.size[0]*ratio/2+"px "+this.image.size[1]*ratio/2+"px";
            let transform = "translate("+left+"px, "+top+"px) rotate("+bbox.angle+"deg)";
            img.style.width = imgWidth;
            img.style.transformOrigin = transformOrigin;
            img.style.transform = transform;

            // Overlay
            let overlay = modalImgContainer.querySelector(".overlay");
            if (this.line.mask) {
                let maskPoints = this.line.mask.map(
                    (pt) => Math.round(pt[0]*ratio)+ ","+
                        Math.round(pt[1]*ratio)).join(" ");
                let polygon = overlay.querySelector("polygon");
                polygon.setAttribute("points", maskPoints);
                overlay.style.width = imgWidth;
                overlay.style.height = this.image.size[1]*ratio+"px";
                overlay.style.transformOrigin = transformOrigin;
                overlay.style.transform = transform;
                overlay.classList.add("show");
            } else {
                // TODO: fake mask?!
                overlay.classList.remove("show");
            }
        },

        computeInputStyles(bbox, ratio, lineHeight, hContext) {
            // Content input
            let container = this.$refs.transInputContainer;
            let input = container.querySelector("#trans-input");
            let verticalTextInput;

            // note: input is not up to date yet
            let content = this.line.currentTrans && this.line.currentTrans.content || "";
            let ruler = document.createElement("span");
            ruler.style.position = "absolute";
            ruler.style.visibility = "hidden";
            ruler.textContent = content;
            ruler.style.whiteSpace="nowrap"

            if(this.mainTextDirection == "ttb"){
                // put the container inline for vertical transcription:
                container.style.display = "inline-block";
                verticalTextInput = container.querySelector("#vertical_text_input");
                // apply vertical writing style to the ruler:
                ruler.style.writingMode = "vertical-lr";
                ruler.style.textOrientation = "upright";
            }

            container.appendChild(ruler);

            let context = hContext*lineHeight;
            let fontSize = Math.max(15, Math.round(lineHeight*0.7));  // Note could depend on the script
            ruler.style.fontSize = fontSize+"px";

            if(this.mainTextDirection != "ttb"){
                input.style.fontSize = fontSize+"px";
                input.style.height = Math.round(fontSize*1.1)+"px";
            }else{
                verticalTextInput.style.fontSize = fontSize+"px";
                verticalTextInput.style.width = Math.round(fontSize*1.1)+"px";
            }

            if (this.readDirection == "rtl") {
                container.style.marginRight = context+"px";
            } else {
                // left to right
                // TODO: deal with other directions
                container.style.marginLeft = context+"px";
            }
            if(this.mainTextDirection != "ttb"){
                if (content) {
                    let lineWidth = bbox.width*ratio;
                    var scaleX = Math.min(5,  lineWidth / ruler.clientWidth);
                    scaleX = Math.max(0.2, scaleX);
                    input.style.transform = "scaleX("+ scaleX +")";
                    input.style.width = 100/scaleX + "%";
                } else {
                    input.style.transform = "none";
                    input.style.width = "100%"; //'calc(100% - '+context+'px)';
                }
            }else{
                let modalImgContainer = this.$refs.modalImgContainer;
                let textInputWrapper = container.querySelector("#textInputWrapper");
                let textInputBorderWrapper = container.querySelector("#textInputBorderWrapper");
                if (content) {
                    let lineWidth = bbox.height*ratio;
                    var scaleY = Math.min(5,  lineWidth / ruler.clientHeight);
                    //var scaleY = Math.min(5,  lineWidth / modalImgContainer.clientHeight);
                    //var scaleY = Math.min(5,  modalImgContainer.clientHeight / ruler.clientHeight);
                    //var scaleY = Math.min(5,  modalImgContainer.clientHeight / textInputWrapper.clientHeight) * 0.7;
                    scaleY = Math.max(0.2, scaleY);
                    verticalTextInput.style.transformOrigin = "top";
                    verticalTextInput.style.transform = "scaleY("+ scaleY +")";
                    //document.getElementById('vertical_text_input').style.height = 100/scaleY + '%'; // not needed here
                } else {
                    verticalTextInput.style.transform = "none";
                    verticalTextInput.style.height = modalImgContainer.clientHeight + "px";
                }
                textInputWrapper.style.height = modalImgContainer.clientHeight + "px";
                // simulate an input field border to fix it to the actual size of the image
                textInputBorderWrapper.style.width = verticalTextInput.clientWidth+"px";
                //textInputBorderWrapper.style.width = verticalTextInput.offsetWidth+'px';
                textInputBorderWrapper.style.height = modalImgContainer.clientHeight+"px";
            }
            container.removeChild(ruler);  // done its job
        },

        computeStyles() {
            /*
               Centers the image on the line (zoom + rotation)
               Modifies input font size and height to match the image
             */
            let modalImgContainer = this.$refs.modalImgContainer;

            let bbox = this.getRotatedLineBBox();
            let hContext = 0.3; // vertical context added around the line, in percentage

            //
            let ratio = 1;
            let lineHeight = 150;

            if(this.mainTextDirection != "ttb")
            {
                ratio = modalImgContainer.clientWidth / (bbox.width + (2*bbox.height*hContext));
                let MAX_HEIGHT = Math.round(Math.max(25, (window.innerHeight-230) / 3));
                lineHeight = Math.max(30, Math.round(bbox.height*ratio));
                if (lineHeight > MAX_HEIGHT) {
                    // change the ratio so that the image can not get too big
                    ratio = (MAX_HEIGHT/lineHeight)*ratio;
                    lineHeight = MAX_HEIGHT;
                }
            }else{ // permutation of sizes for ttb text

                modalImgContainer.style.height=String(window.innerHeight-230) + "px";   //   needed to fix height or ratio is nulled
                ratio = modalImgContainer.clientHeight / (bbox.height + (2*bbox.width*hContext));
                let MAX_WIDTH = 30;
                lineHeight = Math.max(30, Math.round(bbox.width*ratio));

                if (lineHeight > MAX_WIDTH) {
                    // change the ratio so that the image can not get too big
                    ratio = (MAX_WIDTH/lineHeight)*ratio;
                    lineHeight = MAX_WIDTH;
                }
            }

            this.computeImgStyles(bbox, ratio, lineHeight, hContext);
            this.computeInputStyles(bbox, ratio, lineHeight, hContext);
        },

        toggleVK() {
            this.isVKEnabled = !this.isVKEnabled;
            let vks = this.enabledVKs;
            const keyboardEnabledInputs = document.getElementsByClassName(
                "display-virtual-keyboard"
            );
            if (this.isVKEnabled) {
                vks.push(this.documentId);
                this.$store.commit("document/setEnabledVKs", vks);
                // eslint-disable-next-line no-undef
                userProfile.set("VK-enabled", vks);
                for (const input of [...keyboardEnabledInputs]) {
                    // eslint-disable-next-line no-undef
                    enableVirtualKeyboard(input);
                    input.focus();
                }
            } else {
                // Make sure we save changes made before we remove the VK
                this.localTranscription = this.$refs.transInput.value;
                vks.splice(vks.indexOf(this.documentId), 1);
                this.$store.commit("document/setEnabledVKs", vks);
                // eslint-disable-next-line no-undef
                userProfile.set("VK-enabled", vks);
                for (const input of [...keyboardEnabledInputs]) {
                    input.onfocus = (e) => { e.preventDefault() };
                    input.focus();
                    input.blur();
                    // delay is required to refocus, to ensure vk removed
                    setTimeout(() => input.focus(), 200);
                }
            }
        }
    },
});
</script>
