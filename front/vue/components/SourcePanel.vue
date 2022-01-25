<template>
    <div class="col panel">
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
            <div v-if="typo.length > 4" class="dropdown">
              <button class="btn btn-sm btn-info dropdown-toggle"
                      type="button"
                      id="dropdownMenuButton1"
                      data-toggle="dropdown">
                {{ group }}
              </button>
              <ul class="dropdown-menu" aria-labelledby="dropdownMenuButton1">
                <li v-for="taxo in typo">
                  <a class="dropdown-item"
                     :id="'anno-taxo-' + taxo.pk"
                     @click="toggleTaxonomy(taxo, $event)">
                    {{ taxo.name }}</a>
                </li>
              </ul>
            </div>
            <button v-else
                    v-for="taxo in typo"
                    :id="'anno-taxo-' + taxo.pk"
                    @click="toggleTaxonomy(taxo, $event)"
                    class="btn btn-sm btn-outline-info"
                    autocomplete="off">{{ taxo.name }}</button>
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


export default Vue.extend({
    mixins: [BasePanel, AnnoPanel],
    props: ['fullsizeimage'],
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
    mounted: function() {
        this.$parent.zoom.register(
            this.$el.querySelector('#source-zoom-container'),
            {map: true});

        this.initAnnotations();
        // we need to move the annotation editor out of the zoom container
        let img = document.getElementById('source-panel-img');
        this.$refs.content.insertBefore(img.nextElementSibling, null);
    },
    methods: {
        async rotate(angle) {
            await this.$store.dispatch('parts/rotate', angle);
        },

        getCoordinatesFromW3C(annotation) {
            var coordinates = [];
            if (annotation.taxonomy.marker_type == 'Rectangle') {
                // looks like xywh=pixel:133.98072814941406,144.94607543945312,169.30674743652344,141.2919921875"
                let m = annotation.target.selector.value.match(
                    new RegExp(/(?<x>\d+)(.\d+)?,(?<y>\d+)(\.\d+)?,(?<w>\d+)(\.\d+)?,(?<h>\d+)(\.\d+)?/)).groups;
                coordinates = [[parseInt(m.x), parseInt(m.y)],
                               [parseInt(m.x)+parseInt(m.w), parseInt(m.y)+parseInt(m.h)]];
            } else if (annotation.taxonomy.marker_type == 'Polygon') {
                // looks like <svg><polygon points=\"168.08567810058594,230.20848083496094 422.65484619140625,242.38882446289062 198.5365447998047,361.75616455078125\"></polygon></svg>
                let matches = annotation.target.selector.value.matchAll(
                    /(?<x>\d+)(.\d+)?,(?<y>\d+)(.\d+)?/g);
                for (let m of matches) {
                    coordinates.push([m.groups.x, m.groups.y])
                }
            }
            return coordinates;
        },

        async initAnnotations() {
            this.anno = new Annotorious({
                image: document.getElementById('source-panel-img'),
                allowEmpty: true,
                readOnly: true,
                widgets: [],
                disableEditor: false
            });
            let annos = await this.$store.dispatch('imageAnnotations/fetch');

            annos.forEach(function(annotation) {
                let data = annotation.as_w3c;
                data.pk = annotation.pk;
                data.taxonomy = this.$store.state.document.annotationTaxonomies.image.find(e => e.pk == annotation.taxonomy);
                this.anno.addAnnotation(data);
            }.bind(this));

            this.anno.on('createAnnotation', async function(annotation) {
                annotation.taxonomy = this.currentTaxonomy;
                let body = this.getAPIAnnotationBody(annotation);
                body.coordinates = this.getCoordinatesFromW3C(annotation);
                const newAnno = await this.$store.dispatch('imageAnnotations/create', body);
                annotation.pk = newAnno.pk;
            }.bind(this));

            this.anno.on('updateAnnotation', function(annotation) {
                // TODO: change annotation type?!
                // annotation.taxonomy = this.currentTaxonomy;
                let body = this.getAPIAnnotationBody(annotation);
                body.id = annotation.id;
                body.coordinates = this.getCoordinatesFromW3C(annotation);
                this.$store.dispatch('imageAnnotations/update', body);
            }.bind(this));

            this.anno.on('selectAnnotation', function(annotation) {
                this.setAnnoTaxonomy(annotation.taxonomy);
            }.bind(this));

            this.anno.on('deleteAnnotation', function(annotation) {
                this.$store.dispatch('imageAnnotations/delete', annotation.pk);
            }.bind(this));
        },

        setThisAnnoTanomy(taxo) {
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
