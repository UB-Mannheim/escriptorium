window.Vue = require('vue/dist/vue');
import './components/trans_modal.js';
import { partStore } from './store/part.js';
import { SourcePanel } from './components/source_panel.js';
import { SegPanel } from './components/seg_panel.js';
import { VisuPanel } from './components/visu_panel.js';
import { DiploPanel } from './components/diplo_panel.js';

export var partVM = new Vue({
    el: "#part-edit",
    delimiters: ["${","}"],
    data: {
        part: partStore,
        zoom: new WheelZoom(),
        show: {
            source: userProfile.get('source-panel'),
            segmentation: userProfile.get('segmentation-panel'),
            visualisation: userProfile.get('visualisation-panel'),
            diplomatic: userProfile.get('diplomatic-panel')
        },
        blockShortcuts: false,
        fullsizeimage: false,
        selectedTranscription: null,
        comparedTranscriptions: []
    },
    computed: {
        imageSize() {
            return this.part.image.size[0]+'x'+this.part.image.size[1];
        },
        openedPanels() {
            return [this.show.source,
                    this.show.segmentation,
                    this.show.visualisation].filter(p=>p===true);
        },

        zoomScale: {
            get() {
                return this.zoom.scale || 1;
            },
            set(newValue) {
                let target = {
                    x: this.$el.clientWidth/this.openedPanels.length/2-this.zoom.pos.x,
                    y: this.$el.clientHeight/this.openedPanels.length/2-this.zoom.pos.y
                };
                this.zoom.zoomTo(target, parseFloat(newValue)-this.zoom.scale);
            }
        }
    },
    watch: {
        'part.pk': function(n, o) {
            if (n) {
                // set the new url
                window.history.pushState(
                    {}, "",
                    document.location.href.replace(/(part\/)\d+(\/edit)/,
                                                   '$1'+this.part.pk+'$2'));

                // set the 'image' tab btn to select the corresponding image
                var tabUrl = new URL($('#nav-img-tab').attr('href'),
                                     window.location.origin);
                tabUrl.searchParams.set('select', this.part.pk);
                $('#nav-img-tab').attr('href', tabUrl);
            }
        },
        selectedTranscription: function(n, o) {
            let itrans = userProfile.get('initialTranscriptions') || {};
            itrans[DOCUMENT_ID] = n;
            userProfile.set('initialTranscriptions', itrans);
            this.getCurrentContent(n);
        },
        comparedTranscriptions: function(n, o) {
            n.forEach(function(tr, i) {
                if (!o.find(e=>e==tr)) {
                    this.part.fetchContent(tr);
                }
            }.bind(this));
        },

        blockShortcuts(n, o) {
            // make sure the segmenter doesnt trigger keyboard shortcuts either
            if (this.$refs.segPanel) this.$refs.segPanel.segmenter.disableShortcuts = n;
        }
    },

    components: {
        'sourcepanel': SourcePanel,
        'segmentationpanel': SegPanel,
        'visupanel': VisuPanel,
        'diplopanel': DiploPanel,
    },

    created() {
        // this.fetch();
        this.part.fetchPart(PART_ID, function() {
            let tr = userProfile.get('initialTranscriptions')
                  && userProfile.get('initialTranscriptions')[DOCUMENT_ID]
                  || this.part.transcriptions[0].pk;
            this.selectedTranscription = tr;
        }.bind(this));

        // bind all events emited from panels and such
        this.$on('update:transcription', function(lineTranscription) {
            this.part.pushContent(lineTranscription);
        }.bind(this));
        this.$on('create:line', function(line, cb) {
            this.part.createLine(line, this.selectedTranscription, cb);
        }.bind(this));
        this.$on('bulk_create:lines', function(line, cb) {
            this.part.bulkCreateLines(line, this.selectedTranscription, cb);
        }.bind(this));
        this.$on('update:line', function(line, cb) {
            this.part.updateLine(line, cb);
        }.bind(this));
        this.$on('bulk_update:lines', function(lines, cb) {
            this.part.bulkUpdateLines(lines, cb);
        }.bind(this));
        this.$on('delete:line', function(linePk, cb) {
            this.part.deleteLine(linePk, cb);
        }.bind(this));
        this.$on('bulk_delete:lines', function(pks, cb) {
            this.part.bulkDeleteLines(pks, cb);
        }.bind(this));

        this.$on('create:region', function(region, cb) {
            this.part.createRegion(region, cb);
        }.bind(this));
        this.$on('update:region', function(region, cb) {
            this.part.updateRegion(region, cb);
        }.bind(this));
        this.$on('delete:region', function(regionPk, cb) {
            this.part.deleteRegion(regionPk, cb);
        }.bind(this));

        this.$on('bulk_create:transcriptions', function(lines, cb) {
            this.part.bulkCreateLineTranscriptions(lines, cb);
        }.bind(this));

        this.$on('bulk_update:transcriptions', function(lines, cb) {
            this.part.bulkUpdateLineTranscriptions(lines, cb);
        }.bind(this));

        this.$on('move:line', function(movedLines, cb) {
            this.part.move(movedLines, cb);
        }.bind(this));

        document.addEventListener('keydown', function(event) {
            if (this.blockShortcuts) return;
            if (event.keyCode == 33 ||  // page up
                (event.keyCode == (READ_DIRECTION == 'rtl'?39:37) && event.ctrlKey)) {  // arrow left

                this.getPrevious();
                event.preventDefault();
            } else if (event.keyCode == 34 ||   // page down
                       (event.keyCode == (READ_DIRECTION == 'rtl'?37:39) && event.ctrlKey)) {  // arrow right
                this.getNext();
                event.preventDefault();
            } else if (event.keyCode == 8 && event.ctrlKey) {  // backspace
                 this.zoom.reset();
            }
        }.bind(this));

        let debounced = _.debounce(function() {  // avoid calling this too often
            if(this.$refs.segPanel) this.$refs.segPanel.refresh();
            if(this.$refs.visuPanel) this.$refs.visuPanel.refresh();
            if(this.$refs.diploPanel) this.$refs.diploPanel.refresh();
        }.bind(this), 200);
        window.addEventListener('resize', debounced);

        // load the full size image when we reach a scale > 1
        this.zoom.events.addEventListener('wheelzoom.updated', function(ev) {
            if (this.part.loaded && !this.fullsizeimage) {
                let ratio = ev.target.clientWidth / this.part.image.size[0];
                if (this.zoom.scale  * ratio > 1) {
                    this.prefetchImage(this.part.image.uri, function() {
                        this.fullsizeimage = true;
                    }.bind(this));
                }
            }
        }.bind(this));

        // catch background emited events when masks are recalculated
        let $alertsContainer = $('#alerts-container');
        $alertsContainer.on('part:mask', function(ev, data) {
            data.lines.forEach(function(lineData) {
                let line = this.part.lines.find(l=>l.pk == lineData.pk);
                if (line) {  // might have been deleted in the meantime
                    line.mask = lineData.mask;
                }
            }.bind(this));
        }.bind(this));
    },
    methods: {
        resetZoom() {
            this.zoom.reset();
        },
        prefetchImage(src, callback) {
            // this is the panel's responsability to call this!
            let img = new Image();
            img.addEventListener('load', function() {
                if (callback) callback(src);
                img.remove();
            }.bind(this));
            img.src = src;
        },
        deleteTranscription(ev) {
            let transcription = ev.target.dataset.trpk;
            // I lied, it's only archived
            if(confirm("Are you sure you want to delete the transcription?")) {
                this.part.archiveTranscription(transcription);
                ev.target.parentNode.remove();  // meh
                let compInd = this.comparedTranscriptions.findIndex(e=>e.pk == transcription);
                if (compInd != -1) Vue.delete(this.comparedTranscriptions, compInd)
            }
        },
        getCurrentContent(transcription) {
            this.part.fetchContent(transcription, function() {
                this.part.lines.forEach(function(line, i) {
                    if (line.transcriptions[this.selectedTranscription]) {
                        Vue.set(line, 'currentTrans',
                                line.transcriptions[this.selectedTranscription]);
                    }
                }.bind(this));
            }.bind(this));
        },
        getComparisonContent() {
            this.comparedTranscriptions.forEach(function(tr, i) {
                if (tr != this.selectedTranscription) {
                    this.part.fetchContent(tr);
                }
            }.bind(this));
        },
        getPrevious(ev) {
            return this.part.getPrevious(function() {
                this.getCurrentContent(this.selectedTranscription);
                this.getComparisonContent();
            }.bind(this));
        },
        getNext(ev) {
            return this.part.getNext(function() {
                this.getCurrentContent(this.selectedTranscription);
                this.getComparisonContent();
            }.bind(this));
        },

        togglePanel(ev)  {
            let btn = ev.target;
            let target = btn.getAttribute('data-target');
            this.show[target] = !this.show[target];
            userProfile.set(target + '-panel', this.show[target]);

            // wait for css
            Vue.nextTick(function() {
                if(this.$refs.segPanel) this.$refs.segPanel.refresh();
                if(this.$refs.visuPanel) this.$refs.visuPanel.refresh();
                if(this.$refs.diploPanel) this.$refs.diploPanel.refresh();
            }.bind(this));
        },
    }
});
