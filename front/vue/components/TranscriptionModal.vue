<template>
    <div id="trans-modal"
         class="modal"
         tabindex="-1"
         role="dialog">
        <div class="modal-dialog modal-xl" role="document">
            <div class="modal-content">
                <div class="modal-header">
                    <button v-if="readDirection == 'rtl'"
                            type="button"
                            id="next-btn"
                            @click="$parent.editNext()"
                            title="Next"
                            class="btn btn-sm mr-1 btn-secondary">
                        <i class="fas fa-arrow-circle-left"></i>
                    </button>
                    <button v-else
                            type="button"
                            id="prev-btn"
                            @click="$parent.editPrevious()"
                            title="Previous"
                            class="btn btn-sm mr-1 btn-secondary">
                        <i class="fas fa-arrow-circle-left"></i>
                    </button>

                    <button v-if="readDirection == 'rtl'"
                            type="button"
                            id="prev-btn"
                            @click="$parent.editPrevious()"
                            title="Previous"
                            class="btn btn-sm mr-1 btn-secondary">
                        <i class="fas fa-arrow-circle-right"></i>
                    </button>
                    <button v-else
                            type="button"
                            id="next-btn"
                            @click="$parent.editNext()"
                            title="Next"
                            class="btn btn-sm mr-1 btn-secondary">
                        <i class="fas fa-arrow-circle-right"></i>
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
                <div :class="'modal-body ' + defaultTextDirection">
                    <div id="modal-img-container" width="80%">
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

                    <div id="trans-input-container">
                        <input v-on:keyup.down="$parent.editNext"
                                v-on:keyup.up="$parent.editPrevious"
                                id="trans-input"
                                name="content"
                                class="form-control mb-2"
                                v-on:keyup.enter="$parent.editNext"
                                v-model.lazy="localTranscription"
                                autocomplete="off"
                                autofocus/>
                        <small v-if="line.currentTrans && line.currentTrans.version_updated_at" class="form-text text-muted">
                            <span>by {{line.currentTrans.version_author}} ({{line.currentTrans.version_source}})</span>
                            <span>on {{momentDate}}</span>
                        </small>
                    </div>

                    <!-- transcription comparison -->
                    <div v-if="$parent.$parent.comparedTranscriptions.length"
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
                                    <span v-if="trans.pk == $parent.$parent.selectedTranscription">(current)</span></small>
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
    props: ['readDirection', 'defaultTextDirection', 'line'],
    components: {
        LineVersion,
        HelpVersions,
        HelpCompareTranscriptions,
    },
    created() {
        this.$on('update:transcription:version', function(version) {
            this.line.currentTrans.content = version.data.content;
            this.$parent.$parent.$emit('update:transcription', this.line.currentTrans);
        }.bind(this));

        // make sure that typing in the input doesnt trigger keyboard shortcuts
        $(document).on('hide.bs.modal', '#trans-modal', function(ev) {
            this.$parent.editLine = null;
            this.$parent.$parent.blockShortcuts = false;
        }.bind(this));

        $(document).on('show.bs.modal', '#trans-modal', function(ev) {
            this.$parent.$parent.blockShortcuts = true;
        }.bind(this));

        this.timeZone = moment.tz.guess();
    },
    mounted() {
        $(this.$el).modal('show');
        $(this.$el).draggable({handle: '.modal-header'});
        $(this.$el).resizable();
        this.computeStyles();

        let input = this.$el.querySelector('#trans-input');
        input.focus();
    },
    watch: {
        line(new_, old_) {
            this.computeStyles();
        }
    },
    computed: {
        momentDate() {
            return moment.tz(this.line.currentTrans.version_updated_at, this.timeZone);
        },
        modalImgSrc() {
            return this.$parent.$parent.part.image.uri;
        },
        otherTranscriptions() {
            let a = Object
                .keys(this.line.transcriptions)
                .filter(pk=>this.$parent.$parent.comparedTranscriptions
                                .includes(parseInt(pk)))
                .map(pk=>{ return {
                    pk: pk,
                    name: this.$parent.$parent.part.transcriptions.find(e=>e.pk==pk).name,
                    content: this.line.transcriptions[pk].content
                }; });
            return a;
        },
        localTranscription: {
            get() {
                return this.line.currentTrans && this.line.currentTrans.content || '';
            },
            set(newValue) {
                this.line.currentTrans.content = newValue;
                // is this ok ?
                this.$parent.$parent.$emit('update:transcription',
                                           this.line.currentTrans);
            }
        }
    },
    methods: {
        close() {
            $(this.$el).modal('hide');
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
            let p1 = this.line.baseline[0];
            let p2 = this.line.baseline[this.line.baseline.length-1];
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
            let angle = target_angle - this.getLineAngle();

            // apply it to the polygon and get the resulting bbox
            let transformOrigin =  this.$parent.$parent.part.image.size[0]/2+'px '+this.$parent.$parent.part.image.size[1]/2+'px';
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
            let modalImgContainer = this.$el.querySelector('#modal-img-container');
            let img = modalImgContainer.querySelector('img#line-img');

            let context = hContext*lineHeight;
            let visuHeight = lineHeight + 2*context;
            modalImgContainer.style.height = visuHeight+'px';

            let top = -(bbox.top*ratio - context);
            let left = -(bbox.left*ratio - context);
            // modalImgContainer.style.transform = 'scale('+ratio+')';

            let imgWidth = this.$parent.$parent.part.image.size[0]*ratio +'px';
            let transformOrigin =  this.$parent.$parent.part.image.size[0]*ratio/2+'px '+this.$parent.$parent.part.image.size[1]*ratio/2+'px';
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
                overlay.style.height = this.$parent.$parent.part.image.size[1]*ratio+'px';
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
            let container = this.$el.querySelector('#trans-modal #trans-input-container');
            let input = container.querySelector('#trans-input');
            // note: input is not up to date yet
            let content = this.line.currentTrans && this.line.currentTrans.content || '';
            let ruler = document.createElement('span');
            ruler.style.position = 'absolute';
            ruler.style.visibility = 'hidden';
            ruler.textContent = content;
            ruler.style.whiteSpace="nowrap"
            container.appendChild(ruler);

            let context = hContext*lineHeight;
            let fontSize = Math.max(15, Math.round(lineHeight*0.7));  // Note could depend on the script
            ruler.style.fontSize = fontSize+'px';
            input.style.fontSize = fontSize+'px';
            input.style.height = Math.round(fontSize*1.1)+'px';

            if (this.readDirection == 'rtl') {
                container.style.marginRight = context+'px';
            } else {
                // left to right
                // TODO: deal with other directions
                container.style.marginLeft = context+'px';
            }
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
            container.removeChild(ruler);  // done its job
        },

        computeStyles() {
            /*
               Centers the image on the line (zoom + rotation)
               Modifies input font size and height to match the image
             */
            let modalImgContainer = this.$el.querySelector('#modal-img-container');

            let bbox = this.getRotatedLineBBox();
            let hContext = 0.3; // vertical context added around the line, in percentage
            let ratio = modalImgContainer.clientWidth / (bbox.width + (2*bbox.height*hContext));
            let MAX_HEIGHT = Math.round(Math.max(25, (window.innerHeight-230) / 3));
            let lineHeight = Math.max(30, Math.round(bbox.height*ratio));
            if (lineHeight > MAX_HEIGHT) {
                // change the ratio so that the image can not get too big
                ratio = (MAX_HEIGHT/lineHeight)*ratio;
                lineHeight = MAX_HEIGHT;
            }

            this.computeImgStyles(bbox, ratio, lineHeight, hContext);
            this.computeInputStyles(bbox, ratio, lineHeight, hContext);
        },
    },
});
</script>

<style scoped>
</style>