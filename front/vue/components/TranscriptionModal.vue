<template>
    <div id="trans-modal"
         ref="transModal"
         class="modal"
         role="dialog">
        <div class="modal-dialog modal-xl" role="document">
            <div class="modal-content">
                <div class="modal-header">
                    <button v-if="$store.state.document.readDirection == 'rtl'"
                            type="button"
                            id="next-btn"
                            @click="editLine('next')"
                            title="Next (up arrow)"
                            class="btn btn-sm mr-1 btn-secondary">
                        <i class="fas fa-arrow-circle-left"></i>
                    </button>
                    <button v-else
                            type="button"
                            id="prev-btn"
                            @click="editLine('previous')"
                            title="Previous (up arrow)"
                            class="btn btn-sm mr-1 btn-secondary">
                        <i class="fas fa-arrow-circle-left"></i>
                    </button>

                    <button v-if="$store.state.document.readDirection == 'rtl'"
                            type="button"
                            id="prev-btn"
                            @click="editLine('previous')"
                            title="Previous (down arrow)"
                            class="btn btn-sm mr-1 btn-secondary">
                        <i class="fas fa-arrow-circle-right"></i>
                    </button>
                    <button v-else
                            type="button"
                            id="next-btn"
                            @click="editLine('next')"
                            title="Next (down arrow)"
                            class="btn btn-sm mr-1 btn-secondary">
                        <i class="fas fa-arrow-circle-right"></i>
                    </button>
                    <button class="btn btn-sm ml-2 mr-1"
                            :class="{'btn-info': isVKEnabled, 'btn-outline-info': !isVKEnabled}"
                            title="Toggle Virtual Keyboard for this document."
                            @click="toggleVK">
                        <i class="fas fa-keyboard"></i>
                    </button>

                    <h5 class="modal-title ml-3" id="modal-label">
                        Line #{{line.order + 1}}
                    </h5>

                    <button type="button"
                            class="close"
                            @click="close" aria-label="Close">
                        <span aria-hidden="true">&times;</span>
                    </button>
                </div>
                <div :class="'modal-body ' + $store.state.document.defaultTextDirection">
                    <div id="modal-img-container" ref="modalImgContainer" width="80%">
                        <img id="line-img"
                                v-bind:src="modalImgSrc"
                                draggable="false" selectable="false"/>
                        <div class="overlay">
                            <svg width="100%" height="100%">
                                <defs>
                                    <mask id="modal-overlay">
                                        <rect width="100%" height="100%" fill="white"/>
                                        <polygon points=""/>
                                    </mask>
                                </defs>
                                <rect fill="grey" opacity="0.5" width="100%" height="100%" mask="url(#modal-overlay)" />
                            </svg>
                        </div>
                    </div>

                      <div id="trans-input-container" ref="transInputContainer">
                        <input v-if="$store.state.document.mainTextDirection != 'ttb'"
                                v-on:keyup.down="editLine('next')"
                                v-on:keyup.up="editLine('previous')"
                                v-on:keyup.enter="editLine('next')"
                                id="trans-input"
                                ref="transInput"
                                name="content"
                                class="form-control mb-2 display-virtual-keyboard"
                                v-model.lazy="localTranscription"
                                autocomplete="off"
                                autofocus/>
                        <!--Hidden input for ttb text: -->
                        <input v-else
                                id="trans-input"
                                ref="transInput"
                                name="content"
                                type="hidden"
                                v-model.lazy="localTranscription"
                                autocomplete="off" />
                        <!-- in this case, input field is replaced by: -->
                        <div v-if="$store.state.document.mainTextDirection == 'ttb'"
                            id="textInputWrapper">
                            <div id="textInputBorderWrapper" class="form-control mb-2">
                                <div    v-on:blur="localTranscription = $event.target.textContent"
                                        v-on:keyup="recomputeInputCharsScaleY()"
                                        v-on:keyup.right="editLine('next')"
                                        v-on:keyup.left="editLine('previous')"
                                        v-on:keyup.enter="cleanHTMLTags();recomputeInputCharsScaleY();editLine('next')"
                                        v-html="localTranscription"
                                        id="vertical_text_input"
                                        contenteditable="true"
                                        class="display-virtual-keyboard">
                                </div>
                            </div>
                        </div>

                        <small v-if="line.currentTrans && line.currentTrans.version_updated_at" class="form-text text-muted">
                            <span>by {{line.currentTrans.version_author}} ({{line.currentTrans.version_source}})</span>
                            <span>on {{momentDate}}</span>
                        </small>
                    </div>

                    <!-- transcription comparison -->
                    <div v-if="$store.state.transcriptions.comparedTranscriptions.length"
                            class="card history-block mt-2">
                        <div class="card-header">
                            <a href="#"
                                class="card-toggle"
                                data-toggle="collapse"
                                data-target=".compare-show">
                                <span>Toggle transcription comparison</span>
                            </a>

                            <button  title="Help."
                                        data-toggle="collapse"
                                        data-target="#compare-help"
                                        class="btn btn-info fas fa-question help nav-item ml-2"></button>
                            <div id="compare-help" class="alert alert-primary help-text collapse">
                                <HelpCompareTranscriptions></HelpCompareTranscriptions>
                            </div>
                        </div>
                        <div class="d-table card-body compare-show collapse show">
                            <div v-for="trans in otherTranscriptions"
                                    v-bind:key="'TrC' + trans.pk"
                                    class="d-table-row">
                                <div class="d-table-cell col" v-html="comparedContent(trans.content)"></div>
                                <div class="d-table-cell text-muted text-nowrap col" title="Transcription name"><small>
                                    {{ trans.name }}
                                    <span v-if="trans.pk == $store.state.transcriptions.selectedTranscription">(current)</span></small>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- versioning/history -->
                    <div v-if="line.currentTrans && line.currentTrans.versions && line.currentTrans.versions.length"
                            class="card history-block mt-2">
                        <div class="card-header">
                            <a href="#"
                                class="card-toggle collapsed"
                                data-toggle="collapse"
                                data-target=".history-show">
                                <span>Toggle history</span>
                            </a>
                            <button title="Help."
                                    data-toggle="collapse"
                                    data-target="#versions-help"
                                    class="btn btn-info fas fa-question help nav-item ml-2 collapsed"></button>
                            <div id="versions-help"
                                    class="alert alert-primary help-text collapse">
                                <HelpVersions></HelpVersions>
                            </div>
                        </div>
                        <div id="history" class="history-show card-body collapse">
                            <div class="d-table">
                                <LineVersion
                                    v-if="line.currentTrans && line.currentTrans.versions"
                                    v-for="(version, index) in line.currentTrans.versions"
                                    v-bind:previous="line.currentTrans.versions[index+1]"
                                    v-bind:version="version"
                                    v-bind:line="line"
                                    v-bind:key="version.revision">
                                </LineVersion>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import LineVersion from './LineVersion.vue';
import HelpVersions from './HelpVersions.vue';
import HelpCompareTranscriptions from './HelpCompareTranscriptions.vue';

export default Vue.extend({
    data() {
      return {
        isVKEnabled: false
      }
    },
    components: {
        LineVersion,
        HelpVersions,
        HelpCompareTranscriptions,
    },
    created() {
        // make sure that typing in the input doesnt trigger keyboard shortcuts
        $(document).on('hide.bs.modal', '#trans-modal', function(ev) {
            if (this.isVKEnabled) {
                for (const input of [...document.getElementsByClassName("display-virtual-keyboard")])
                    input.blur();
            }
            this.$store.dispatch('lines/toggleLineEdition', null);
            this.$store.commit('document/setBlockShortcuts', false);
        }.bind(this));

        $(document).on('show.bs.modal', '#trans-modal', function(ev) {
            this.$store.commit('document/setBlockShortcuts', true);
        }.bind(this));

        this.timeZone = moment.tz.guess();
    },
    mounted() {
        $(this.$refs.transModal).modal('show');
        $(this.$refs.transModal).draggable({handle: '.modal-header'});
        $(this.$refs.transModal).resizable();
        this.computeStyles();
        let modele = this;

        let input = this.$refs.transInput;

        // no need to make focus on hidden input with a ttb text
        if(this.$store.state.document.mainTextDirection != 'ttb'){
            input.focus();
        }else{  // avoid some br or other html tag for a copied text on an editable input div (vertical_text_input):
            //
            document.getElementById("vertical_text_input").addEventListener("paste", function(e) {

                // cancel paste to treat its content before inserting it
                e.preventDefault();

                // get text representation of clipboard
                var text = (e.originalEvent || e).clipboardData.getData('text/plain');
                this.innerHTML = text;
                modele.recomputeInputCharsScaleY();

            }, false);
        }


        this.isVKEnabled = this.$store.state.document.enabledVKs.indexOf(this.$store.state.document.id) != -1 || false;
        if (this.isVKEnabled)
            for (const input of [...document.getElementsByClassName("display-virtual-keyboard")])
                enableVirtualKeyboard(input);
    },
    watch: {
        line(new_, old_) {
            this.computeStyles();
        },
        '$store.state.document.enabledVKs'() {
            this.isVKEnabled = this.$store.state.document.enabledVKs.indexOf(this.$store.state.document.id) != -1 || false;
        }
    },
    computed: {
        line () {
            return this.$store.state.lines.editedLine
        },
        momentDate() {
            return moment.tz(this.line.currentTrans.version_updated_at, this.timeZone);
        },
        modalImgSrc() {
             if (this.$store.state.parts.image.uri.endsWith('.tif') ||
                 this.$store.state.parts.image.uri.endsWith('.tiff')) {
                 // can't display tifs so fallback to large thumbnail
                 return this.$store.state.parts.image.thumbnails.large;
             } else {
                 return this.$store.state.parts.image.uri;
             }
        },
        otherTranscriptions() {
            let a = Object
                .keys(this.line.transcriptions)
                .filter(pk=>this.$store.state.transcriptions.comparedTranscriptions
                                .includes(parseInt(pk)))
                .map(pk=>{ return {
                    pk: pk,
                    name: this.$store.state.transcriptions.all.find(e=>e.pk==pk).name,
                    content: this.line.transcriptions[pk].content
                }; });
            return a;
        },
        localTranscription: {
            get: function() {
                return this.line.currentTrans && this.line.currentTrans.content || '';
            },
            set: async function(newValue) {
                if (this.$refs.transInput.value != newValue) {
                   // Note: better way to do that?
                   this.$refs.transInput.value = newValue;
                   this.computeStyles();
                }
                await this.$store.dispatch('transcriptions/updateLineTranscriptionVersion', { line: this.line, content: newValue });
            }
        },
    },
    methods: {
        close() {
            $(this.$refs.transModal).modal('hide');
        },

        editLine(direction) {
           // making sure the line is saved (it isn't in case of shortcut usage)
           this.localTranscription = this.$refs.transInput.value;
           this.$store.dispatch('lines/editLine', direction);
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
                    return '<span class="cmp-del">'+part.value+'</span>';
                } else if (part.added) {
                    return '<span class="cmp-add">'+part.value+'</span>';
                } else {
                    return part.value;
                }
            }.bind(this)).join('');
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
                    pt => Math.round(pt[0])+ ','+
                        Math.round(pt[1])).join(' ');
            } else {
                // TODO
            }
            let svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            let tmppoly = document.createElementNS('http://www.w3.org/2000/svg',
                                                   'polygon');
            tmppoly.setAttributeNS(null, 'points', maskPoints);
            tmppoly.setAttributeNS(null, 'fill', 'red');

            // calculate rotation needed to get the line horizontal
            let target_angle = 0;  // all lines should be topologically ltr
            if(this.$store.state.document.mainTextDirection == 'ttb') // add a 90 angle for vertical texts
                target_angle = 90;
            let angle = target_angle - this.getLineAngle();

            // apply it to the polygon and get the resulting bbox
            let transformOrigin =  this.$store.state.parts.image.size[0]/2+'px '+this.$store.state.parts.image.size[1]/2+'px';
            tmppoly.style.transformOrigin = transformOrigin;
            tmppoly.style.transform = 'rotate('+angle+'deg)';
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
            let img = modalImgContainer.querySelector('img#line-img');

            let context = hContext*lineHeight;
            let visuHeight = lineHeight + 2*context;

            if(this.$store.state.document.mainTextDirection != 'ttb'){
                modalImgContainer.style.height = visuHeight+'px';
            }else{
                modalImgContainer.style.width = visuHeight+'px';
                modalImgContainer.style.display = 'inline-block';
                modalImgContainer.style.verticalAlign = 'top';
            }
            let top = -(bbox.top*ratio - context);
            let left = -(bbox.left*ratio - context);

            // if text direction is rtl and the line doesn't take all the space,
            // align it to the right
            if (modalImgContainer.clientWidth - 2*context > bbox.width*ratio
                && this.$store.state.document.defaultTextDirection == 'rtl') {
                left += modalImgContainer.clientWidth - 2*context - bbox.width*ratio;
            }

            // modalImgContainer.style.transform = 'scale('+ratio+')';

            let imgWidth = this.$store.state.parts.image.size[0]*ratio +'px';
            let transformOrigin =  this.$store.state.parts.image.size[0]*ratio/2+'px '+this.$store.state.parts.image.size[1]*ratio/2+'px';
            let transform = 'translate('+left+'px, '+top+'px) rotate('+bbox.angle+'deg)';
            img.style.width = imgWidth;
            img.style.transformOrigin = transformOrigin;
            img.style.transform = transform;

            // Overlay
            let overlay = modalImgContainer.querySelector('.overlay');
            if (this.line.mask) {
                let maskPoints = this.line.mask.map(
                    pt => Math.round(pt[0]*ratio)+ ','+
                        Math.round(pt[1]*ratio)).join(' ');
                let polygon = overlay.querySelector('polygon');
                polygon.setAttribute('points', maskPoints);
                overlay.style.width = imgWidth;
                overlay.style.height = this.$store.state.parts.image.size[1]*ratio+'px';
                overlay.style.transformOrigin = transformOrigin;
                overlay.style.transform = transform;
                overlay.style.display = 'block';
            } else {
                // TODO: fake mask?!
                overlay.style.display = 'none';
            }
        },

        computeInputStyles(bbox, ratio, lineHeight, hContext) {
            // Content input
            let container = this.$refs.transInputContainer;
            let input = container.querySelector('#trans-input');
            let verticalTextInput;

            // note: input is not up to date yet
            let content = this.line.currentTrans && this.line.currentTrans.content || '';
            let ruler = document.createElement('span');
            ruler.style.position = 'absolute';
            ruler.style.visibility = 'hidden';
            ruler.textContent = content;
            ruler.style.whiteSpace="nowrap"

            if(this.$store.state.document.mainTextDirection == 'ttb'){
                // put the container inline for vertical transcription:
                container.style.display = 'inline-block';
                verticalTextInput = container.querySelector('#vertical_text_input');
                // apply vertical writing style to the ruler:
                ruler.style.writingMode = 'vertical-lr';
                ruler.style.textOrientation = 'upright';
            }

            container.appendChild(ruler);

            let context = hContext*lineHeight;
            let fontSize = Math.max(15, Math.round(lineHeight*0.7));  // Note could depend on the script
            ruler.style.fontSize = fontSize+'px';

            if(this.$store.state.document.mainTextDirection != 'ttb'){
                input.style.fontSize = fontSize+'px';
                input.style.height = Math.round(fontSize*1.1)+'px';
            }else{
                verticalTextInput.style.fontSize = fontSize+'px';
                verticalTextInput.style.width = Math.round(fontSize*1.1)+'px';
            }

            if (this.$store.state.document.readDirection == 'rtl') {
                container.style.marginRight = context+'px';
            } else {
                // left to right
                // TODO: deal with other directions
                container.style.marginLeft = context+'px';
            }
            if(this.$store.state.document.mainTextDirection != 'ttb'){
                if (content) {
                    let lineWidth = bbox.width*ratio;
                    var scaleX = Math.min(5,  lineWidth / ruler.clientWidth);
                    scaleX = Math.max(0.2, scaleX);
                    input.style.transform = 'scaleX('+ scaleX +')';
                    input.style.width = 100/scaleX + '%';
                } else {
                    input.style.transform = 'none';
                    input.style.width = '100%'; //'calc(100% - '+context+'px)';
                }
            }else{
                let modalImgContainer = this.$refs.modalImgContainer;
                let textInputWrapper = container.querySelector('#textInputWrapper');
                let textInputBorderWrapper = container.querySelector('#textInputBorderWrapper');
                if (content) {
                    let lineWidth = bbox.height*ratio;
                    var scaleY = Math.min(5,  lineWidth / ruler.clientHeight);
                    //var scaleY = Math.min(5,  lineWidth / modalImgContainer.clientHeight);
                    //var scaleY = Math.min(5,  modalImgContainer.clientHeight / ruler.clientHeight);
                    //var scaleY = Math.min(5,  modalImgContainer.clientHeight / textInputWrapper.clientHeight) * 0.7;
                    scaleY = Math.max(0.2, scaleY);
                    verticalTextInput.style.transformOrigin = 'top';
                    verticalTextInput.style.transform = 'scaleY('+ scaleY +')';
                    //document.getElementById('vertical_text_input').style.height = 100/scaleY + '%'; // not needed here
                } else {
                    verticalTextInput.style.transform = 'none';
                    verticalTextInput.style.height = modalImgContainer.clientHeight + 'px';
                }
                textInputWrapper.style.height = modalImgContainer.clientHeight + 'px';
                // simulate an input field border to fix it to the actual size of the image
                textInputBorderWrapper.style.width = verticalTextInput.clientWidth+'px';
                //textInputBorderWrapper.style.width = verticalTextInput.offsetWidth+'px';
                textInputBorderWrapper.style.height = modalImgContainer.clientHeight+'px';
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

            if(this.$store.state.document.mainTextDirection != 'ttb')
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
            let vks = this.$store.state.document.enabledVKs;
            if (this.isVKEnabled) {
                vks.push(this.$store.state.document.id);
                this.$store.commit('document/setEnabledVKs', vks);
                userProfile.set("VK-enabled", vks);
                for (const input of [...document.getElementsByClassName("display-virtual-keyboard")])
                    enableVirtualKeyboard(input);
            } else {
                // Make sure we save changes made before we remove the VK
                this.localTranscription = this.$refs.transInput.value;
                vks.splice(vks.indexOf(this.$store.state.document.id), 1);
                this.$store.commit('document/setEnabledVKs', vks);
                userProfile.set("VK-enabled", vks);
                for (const input of [...document.getElementsByClassName("display-virtual-keyboard")])
                    input.onfocus = (e) => { e.preventDefault() };
            }
        }
    },
});
</script>

<style scoped>
</style>
