<template>
    <div class="col panel">
        <loading :active.sync="isWorking" :is-full-page="false" />
        <div class="tools">
            <i title="Source Panel" class="panel-icon fas fa-eye"></i>
            <a v-bind:href="$store.state.parts.image.uri" target="_blank">
                <button class="btn btn-sm btn-info ml-3 fas fa-download"
                        title="Download full size image" download></button>
            </a>
            <div class="btn-group">
                <button id="rotate-counter-clock"
                        @click="rotate(360-90)"
                        title="Rotate 90° counter-clockwise."
                        class="btn btn-sm btn-info ml-3 fas fa-undo"
                        autocomplete="off">R</button>
                <button id="rotate-clock"
                        @click="rotate(90)"
                        title="Rotate 90° clockwise."
                        class="btn btn-sm btn-info  fas fa-redo"
                        autocomplete="off">R</button>
            </div>

            <div class="btn-group taxo-group ml-2"
                 v-for="typo,group in groupedTaxonomies">
            <button v-for="taxo in typo"
                    :id="'anno-taxo-' + taxo.pk"
                    @click="toggleTaxonomy(taxo)"
                    class="btn btn-sm btn-outline-info"
                    :title="taxo.name"
                    autocomplete="off">{{ taxo.abbreviation ? taxo.abbreviation : taxo.name }}</button>
            </div>
        </div>
        <div ref="content" class="content-container">
            <div id="source-zoom-container" class="content">
                <img id="source-panel-img" ref="img" class="panel-img" v-bind:src="imageSrc"/>
                <div class="overlay panel-overlay">
                    <svg width="100%" height="100%">
                        <defs>
                            <mask id="source-overlay">
                                <rect width="100%"
                                        height="100%"
                                        fill="white"/>
                                <polygon points=""/>
                            </mask>
                        </defs>
                        <rect fill="grey"
                                opacity="0.5"
                                width="100%"
                                height="100%"
                                mask="url(#source-overlay)" />
                    </svg>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import { assign } from 'lodash'
import { BasePanel } from '../../src/editor/mixins.js';
import { AnnoPanel } from '../../src/editor/mixins.js';
import { Annotorious } from '@recogito/annotorious';
import Loading from "vue-loading-overlay";

const rectangleRegExp = new RegExp(/(?<x>\d+)(?:\.\d+)?,(?<y>\d+)(?:\.\d+)?,(?<w>\d+)(?:\.\d+)?,(?<h>\d+)(?:\.\d+)?/);
const polygonRegExp = new RegExp(/(?<x>\d+)(?:\.\d+)?,(?<y>\d+)(?:\.\d+)?/g);

export default Vue.extend({
    mixins: [BasePanel, AnnoPanel],
    props: ['fullsizeimage'],
    data() { return {
        imageLoaded: false,
        isWorking: false
    };},
    components: {
        loading: Loading,
    },
    computed: {
        imageSrc() {
            let src = !this.fullsizeimage
                   && this.$store.state.parts.image.thumbnails.large
                   || this.$store.state.parts.image.uri;
            return src;
        },
        groupedTaxonomies() {
            return _.groupBy(this.$store.state.document.annotationTaxonomies.image,
                             function(taxo) {
                                 return taxo.typology && taxo.typology.name
                             });
        }
    },
    watch: {
        fullsizeimage: function (n, o) {
            // it was prefetched
            if (n && n != o) {
                if (this.anno) {
                    this.imageLoaded = false;
                }
            }
        }
    },
    beforeDestroy: function() {
        this.anno.destroy();
    },
    mounted: function() {
        this.$parent.zoom.register(
            this.$el.querySelector('#source-zoom-container'),
            {map: true});

        this.$refs.img.addEventListener(
            "load",
            function (ev) {
                this.onImageLoaded();
            }.bind(this)
        );

        this.initAnnotations();
        this.fetchAnnotations();
    },
    methods: {
        async rotate(angle) {
            try {
                this.isWorking = true;
                await this.$store.dispatch('parts/rotate', angle);
                this.loadAnnotations();
            } catch {
                // oh well
            } finally {
                this.isWorking = false;
            }
        },

        async onImageLoaded() {
            this.imageLoaded = true;
            this.loadAnnotations();
        },

        getCoordinatesFromW3C(annotation) {
            var coordinates = [];
            if (annotation.target.selector.type == 'FragmentSelector') {
                // looks like xywh=pixel:133.98072814941406,144.94607543945312,169.30674743652344,141.2919921875"
                let m = annotation.target.selector.value.match(rectangleRegExp).groups;
                coordinates = [[parseInt(m.x), parseInt(m.y)],
                               [parseInt(m.x)+parseInt(m.w), parseInt(m.y)],
                               [parseInt(m.x)+parseInt(m.w), parseInt(m.y)+parseInt(m.h)],
                               [parseInt(m.x), parseInt(m.y)+parseInt(m.h)]
                              ];
            } else if (annotation.target.selector.type == 'SvgSelector') {
                // looks like <svg><polygon points=\"168.08567810058594,230.20848083496094 422.65484619140625,242.38882446289062 198.5365447998047,361.75616455078125\"></polygon></svg>
                let matches = annotation.target.selector.value.matchAll(polygonRegExp);
                for (let m of matches) {
                    coordinates.push([m.groups.x, m.groups.y])
                }
            }
            const scale = this.$refs.img.naturalWidth / this.$store.state.parts.image.size[0];
            return coordinates.map(function(pt) {
                // convert a point from UI coordinates to real image coordinates
                return [
                    parseInt(pt[0] / scale),
                    parseInt(pt[1] / scale)
                ];
            }.bind(this));
        },

        makeTaxonomiesStyles() {
            let style = document.createElement('style');
            style.type = 'text/css';
            style.id = 'anno-img-taxonomies-styles';
            document.getElementsByTagName('head')[0].appendChild(style);
            this.$store.state.document.annotationTaxonomies.image.forEach(taxo => {
                let className = 'anno-' + taxo.pk;
                style.innerHTML += "\n ." + className + " .a9s-inner {stroke: " + taxo.marker_detail + ";}";
            });
        },

        async fetchAnnotations() {
            await this.$store.dispatch('imageAnnotations/fetch');
            if (this.imageLoaded) this.loadAnnotations();
        },

        initAnnotations() {
            if (document.getElementById('anno-taxonomies-styles') == null)
                this.makeTaxonomiesStyles();

            var imgAnnoFormatter = function(annotation) {
               let anno = annotation.underlying;
               let className = "anno-" + (anno.taxonomy != undefined && anno.taxonomy.pk || this.currentTaxonomy.pk);
               return className;
            };

            this.anno = new Annotorious({
                image: document.getElementById('source-panel-img'),
                allowEmpty: true,
                readOnly: true,
                widgets: [],
                disableEditor: false,
                formatters: imgAnnoFormatter.bind(this)
            });

            // We need to move the annotation editor out of the zoom container
            const img = document.getElementById('source-panel-img');
            this.$refs.content.insertBefore(img.nextElementSibling, null);

            // The annotation editor doesn't take zoom into account
            var zoom = this.$parent.zoom;
            zoom.events.addEventListener(
                "wheelzoom.updated",
                function (e) {
                    this.fixEditorPosition();
                }.bind(this)
            );

            const isEditorOpen = function(mutationsList, observer) {
                for (let mutation of mutationsList) {
                    if (mutation.addedNodes.length) {
                        this.fixEditorPosition();
                        this.$store.commit('document/setBlockShortcuts', true);
                    } else if (mutation.removedNodes.length) {
                        this.$store.commit('document/setBlockShortcuts', false);
                    }
                }
            }.bind(this);
            const editorObserver = new MutationObserver(isEditorOpen);
            editorObserver.observe(this.anno._appContainerEl, {childList: true});

            this.anno.on('createAnnotation', async function(annotation) {
                annotation.taxonomy = this.currentTaxonomy;
                let body = this.getAPIAnnotationBody(annotation);
                body.coordinates = this.getCoordinatesFromW3C(annotation);
                const newAnno = await this.$store.dispatch('imageAnnotations/create', body);
                annotation.id = newAnno.pk;
            }.bind(this));

            this.anno.on('updateAnnotation', function(annotation) {
                let body = this.getAPIAnnotationBody(annotation);
                body.id = annotation.id;
                body.coordinates = this.getCoordinatesFromW3C(annotation);
                this.$store.dispatch('imageAnnotations/update', body);
            }.bind(this));

            this.anno.on('selectAnnotation', function(annotation) {
                if (this.currentTaxonomy != annotation.taxonomy) {
                    this.toggleTaxonomy(annotation.taxonomy);
                    // have to use this trick to make it editable..
                    this.anno.selectAnnotation();
                    this.anno.selectAnnotation(annotation);
                }
            }.bind(this));

            this.anno.on('deleteAnnotation', function(annotation) {
                this.$store.dispatch('imageAnnotations/delete', annotation.id);
            }.bind(this));
        },

        updateW3CCoordsToUIImg(selector) {
            // coordinates are stored for real size image,
            // we need to pass actual thumbnail coords to annotorious
            const scale = this.$refs.img.naturalWidth / this.$store.state.parts.image.size[0];
            if (selector.type == 'FragmentSelector') {
                return selector.value.replace(rectangleRegExp, function(match, x, y, w, h) {
                    return parseInt(x * scale) + ',' +
                        parseInt(y * scale) + ',' +
                        parseInt(w * scale) + ',' +
                        parseInt(h * scale);
                });
            } else if (selector.type == 'SvgSelector') {
                return selector.value.replace(polygonRegExp, function(match, x, y) {
                    return [
                        parseInt(x * scale),
                        parseInt(y * scale)
                    ];
                });
            }
        },

        loadAnnotations() {
            this.anno.clearAnnotations();
            const annos = this.$store.state.imageAnnotations.all;
            annos.forEach(function(annotation) {
                // ugly way to deep copy so that we don't modify data in the store
                let data = JSON.parse(JSON.stringify(annotation.as_w3c));
                data.id = annotation.pk;
                data.taxonomy = this.$store.state.document.annotationTaxonomies.image.find(e => e.pk == annotation.taxonomy);
                data.target.selector.value = this.updateW3CCoordsToUIImg(data.target.selector);
                this.anno.addAnnotation(data);
            }.bind(this));
        },

        fixEditorPosition() {
            const zoom = this.$parent.zoom;
            const editor = this.anno._appContainerEl.firstChild;
            if (editor) editor.style.transform = 'translate('+(zoom.pos.x)+'px,'+(zoom.pos.y)+'px)';
        },

        setThisAnnoTaxonomy(taxo) {
            this.setImgAnnoTaxonomy(taxo);
        },

        setImgAnnoTaxonomy(taxo) {
            let marker_map = {
                'Rectangle': 'rect',
                'Polygon': 'polygon'
            };
            this.anno.setDrawingTool(marker_map[taxo.marker_type]);
            this.setAnnoTaxonomy(taxo);
        }
    }
});
</script>

<style scoped>
</style>
