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
                 v-for="typo in groupedTaxonomies">
                <button v-for="taxo in typo"
                        :data-taxo="taxo"
                        :id="'anno-taxo-' + taxo.pk"
                        @click="setAnnoTaxonomy(taxo, $event)"
                        title=""
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
import { Annotorious } from '@recogito/annotorious';

var KeyValueWidget = function(args) {
    var purpose = 'attribute-'+args.name;
    var currentValue = args.annotation ?
        args.annotation.bodies.find(b => b.purpose == purpose)
        : null;

    var addTag = function(evt) {
        if (currentValue) {
            args.onUpdateBody(currentValue, {
                type: 'TextualBody',
                purpose: purpose,
                value: evt.target.value
            });
        } else {
            args.onAppendBody({
                type: 'TextualBody',
                purpose: purpose,
                value: evt.target.value
            });
        }
    };

    var container = document.createElement('div');
    container.className = 'r6o-widget keyvalue-widget r6o-nodrag';
    var wid = "anno-widget-"+args.name;
    var label = document.createElement('label');
    label.htmlFor = wid;
    label.innerText = args.name;
    container.append(label);
    if (args.values.length) {
        var input = document.createElement('select');
        args.values.forEach(v => {
            let opt = document.createElement('option');
            opt.value = v;
            opt.text = v;
            if (currentValue && currentValue.value == v) opt.selected = true;
            input.append(opt);
        });
    } else {
        var input = document.createElement('input');
        if (currentValue) input.value = currentValue.value;
    }

    input.id = wid;
    container.append(input);
    input.addEventListener('change', addTag);
    return container;
}

export default Vue.extend({
    mixins: [BasePanel],
    props: ['fullsizeimage'],
    data() { return {
        currentTaxonomy: null,
    };},
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
                let coordinates = [];
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

                const newAnno = await this.$store.dispatch('imageAnnotations/create', {
                    part: this.$store.state.parts.pk,
                    taxonomy: annotation.taxonomy.pk,
                    comments: [...annotation.body.filter(e => e.purpose == 'commenting')].map(b => b.value),
                    components: [...annotation.body.filter(e=> e.purpose.startsWith('attribute'))].map(b => {
                        return {
                            'taxonomy': annotation.taxonomy.components.find(c => 'attribute-'+c.name == b.purpose).pk,
                            'value': b.value
                        }
                    }),

                    coordinates: coordinates
                });
                annotation.pk = newAnno.pk;
            }.bind(this));

            this.anno.on('updateAnnotation', function(annotation) {
                // TODO
                console.log('update', annotation);
            }.bind(this));

            this.anno.on('selectAnnotation', function(annotation) {
                this.setAnnoTaxonomy(annotation.taxonomy);
            }.bind(this));

            this.anno.on('deleteAnnotation', function(annotation) {
                this.$store.dispatch('imageAnnotations/delete', annotation.pk);
            }.bind(this));
        },

        setAnnoTaxonomy(taxo, ev) {
            if (ev) var btn = ev.target;
            if (this.currentTaxonomy == taxo) {
                if (btn) {
                    // toggle annotations off
                    this.anno.readOnly = true;
                    this.currentTaxonomy = null;
                    btn.classList.add('btn-outline-info');
                    btn.classList.remove('btn-info');
                }
            } else {
                document.querySelectorAll('.taxo-group .btn-info').forEach(
                    e => {e.classList.remove('btn-info');
                          e.classList.add('btn-outline-info') });
                this.anno.readOnly = false;
                this.currentTaxonomy = taxo;
                if (btn) {
                    btn.classList.remove('btn-outline-info');
                    btn.classList.add('btn-info');
                }
            }

            let marker_map = {
                'Rectangle': 'rect',
                'Polygon': 'polygon'
            }
            this.anno.setDrawingTool(marker_map[taxo.marker_type]);

            if (taxo.has_comments || taxo.components.length) {
                this.anno.disableEditor = false;
            } else {
                this.anno.disableEditor = true;
            }
            let widgets = [];
            if (taxo.has_comments) {
                widgets.push('COMMENT');
            }
            taxo.components.forEach(compo => {
                widgets.push({widget: KeyValueWidget,
                              name: compo.name,
                              values: compo.allowed_values});
            })

            this.anno.widgets = widgets;
        }
    }
});
</script>

<style scoped>
</style>
