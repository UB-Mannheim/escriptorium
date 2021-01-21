/*
   Baseline editor panel (or segmentation panel)
 */
import { BasePanel } from './base_panel.js';
import { segRegion, segLine } from './seg_line.js';
import { Segmenter } from '../../baseline.editor.js';

export const SegPanel = BasePanel.extend({
    props: ['part', 'fullsizeimage'],
    data() { return {
        segmenter: {loaded: false},
        imgloaded: false,
        colorMode: 'color',  //  color - binary - grayscale
        undoManager: new UndoManager()
    };},
    components: {
        'segline': segLine,
        'segregion': segRegion
    },
    mounted() {
        // wait for the element to be rendered
        Vue.nextTick(function() {
            this.$parent.zoom.register(this.$el.querySelector('#seg-zoom-container'),
                                       {map: true});
            let beSettings = userProfile.get('baseline-editor-'+DOCUMENT_ID) || {};
            this.$img = this.$el.querySelector('img');

            this.segmenter = new Segmenter(this.$img, {
                delayInit:true,
                idField:'pk',
                defaultTextDirection: TEXT_DIRECTION.slice(-2),
                regionTypes: this.part.types.regions.map(t=>t.name),
                lineTypes: this.part.types.lines.map(t=>t.name),
                baselinesColor: beSettings['color-baselines'] || null,
                regionColors: beSettings['color-regions'] || null,
                directionHintColors: beSettings['color-directions'] || null
            });
            // we need to move the baseline editor canvas up one tag so that it doesn't get caught by wheelzoom.
            let canvas = this.segmenter.canvas;
            canvas.parentNode.parentNode.appendChild(canvas);

            // already mounted with a part = opening the panel after page load
            if (this.part.loaded) {
                this.initSegmenter();
            }

            // simulates wheelzoom for canvas
            var zoom = this.$parent.zoom;
            zoom.events.addEventListener('wheelzoom.updated', function(e) {
                this.updateZoom();
            }.bind(this));

            this.segmenter.events.addEventListener('baseline-editor:settings', function(ev) {
                let key = 'baseline-editor-'+DOCUMENT_ID;
                let settings = userProfile.get(key) || {};
                settings[event.detail.name] = event.detail.value;
                userProfile.set(key, settings);
            }.bind(this));
            this.segmenter.events.addEventListener('baseline-editor:delete', function(ev) {
                let data = ev.detail;
                this.bulkDelete(data);
                this.pushHistory(
                    function() { this.bulkCreate(data, createInEditor=true); }.bind(this),
                    function() { this.bulkDelete(data); }.bind(this)
                );
            }.bind(this));
            this.segmenter.events.addEventListener('baseline-editor:update', function(ev) {
                // same event for creation and modification of a line/region
                let data = ev.detail;
                this.extractPrevious(data);
                let toCreate = {
                    lines: data.lines && data.lines.filter(l=>l.context.pk===null) || [],
                    regions: data.regions && data.regions.filter(l=>l.context.pk===null) || []
                };
                let toUpdate = {
                    lines: data.lines && data.lines.filter(l=>l.context.pk!==null) || [],
                    regions: data.regions && data.regions.filter(l=>l.context.pk!==null) || []
                };
                this.bulkCreate(toCreate);
                this.bulkUpdate(toUpdate);
                this.pushHistory(
                    function() {    // undo
                        this.bulkDelete(toCreate);
                        this.bulkUpdate({
                            lines: toUpdate.lines.map(l=>l.previous),
                            regions: toUpdate.regions.map(r=>r.previous)
                        });
                    }.bind(this),
                    function() {   // redo
                        this.bulkCreate(toCreate, createInEditor=true);
                        this.bulkUpdate(toUpdate);
                    }.bind(this)
                );
            }.bind(this));
        }.bind(this));

        // history
        this.$el.querySelector('#undo').addEventListener('click', function(ev) {
            this.undo();
        }.bind(this));
        this.$el.querySelector('#redo').addEventListener('click', function(ev) {
            this.redo();
        }.bind(this));
        document.addEventListener('keyup', function(ev) {
            if (ev.ctrlKey) {
                if (ev.key == 'z') this.undo();
                if (ev.key == 'y') this.redo();
            }
        }.bind(this));
    },
    computed: {
        hasBinaryColor() {
            return this.part.loaded && this.part.bw_image !== null;
        },
        loaded() {
            // for this panel we need both the image and the segmenter
            return this.segmenter && this.segmenter.loaded && this.$img.complete;
        },
        imageSrc() {
            // empty the src to make sure the complete event gets fired
            // this.$img.src = '';
            if (!this.part.loaded) return '';
            // overrides imageSrc to deal with color modes
            // Note: vue.js doesn't have super call wtf we need to copy the code :(
            let src = !this.fullsizeimage
                   && this.part.image.thumbnails.large
                   || this.part.image.uri;

            let bwSrc = (this.colorMode == 'binary'
                      && this.part.bw_image
                      && this.part.bw_image.uri)
                     || src;

            return bwSrc;
        }
    },
    watch: {
        'part.loaded': function(isLoaded, wasLoaded) {
            if (isLoaded===true) {
                if (this.colorMode !== 'binary' && !this.hasBinaryColor) {
                    this.colorMode = 'color';
                }
                this.initSegmenter();
            } else {
                this.segmenter.reset();
                this.undoManager.clear();
                this.refreshHistoryBtns();
            }
        },
        'colorMode': function(n, o) {
            this.$parent.prefetchImage(this.imageSrc, function(src) {
                this.$img.src = src;
                this.refreshSegmenter();
            }.bind(this));
        },
        'fullsizeimage': function(n, o) {
            // it was prefetched
            if (n && n != o) {
                this.$img.src = this.imageSrc;
                this.segmenter.scale = 1;
                this.segmenter.refresh();
            }
        }
    },
    methods: {
        toggleBinary(ev) {
            if (this.colorMode == 'color') this.colorMode = 'binary';
            else this.colorMode = 'color';
        },

        pushHistory(undo, redo) {
            this.undoManager.add({
                undo: undo,
                redo: redo
            });
            this.refreshHistoryBtns();
        },
        initSegmenter() {
            this.$parent.prefetchImage(this.imageSrc, function(src) {
                this.$img.src = src;
                this.refreshSegmenter();
            }.bind(this));
        },
        refreshSegmenter() {
            Vue.nextTick(function() {
                this.segmenter.scale = this.$img.naturalWidth / this.part.image.size[0];
                if (this.segmenter.loaded) {
                    this.segmenter.refresh();
                } else {
                    this.segmenter.init();
                }
            }.bind(this));
        },
        updateZoom() {
            // might not be mounted yet
            if (this.segmenter && this.$img.complete) {
                var zoom = this.$parent.zoom;
                this.segmenter.canvas.style.top = zoom.pos.y + 'px';
                this.segmenter.canvas.style.left = zoom.pos.x + 'px';
                this.segmenter.refresh();
            }
        },
        updateView() {
            if (this.segmenter.loaded) {
                this.segmenter.refresh();
            }
        },
        // undo manager helpers
        bulkCreate(data, createInEditor=false) {
            if (data.regions && data.regions.length) {
                // note: regions dont get a bulk_create
                for (let i=0; i<data.regions.length; i++)  {
                    this.$parent.$emit(
                        'create:region', {
                            pk: data.regions[i].pk,
                            box: data.regions[i].box,
                            type: data.regions[i].type
                        }, function(region) {
                            if (createInEditor) {
                                this.segmenter.loadRegion(region);
                            }
                            // also update pk in the original data for undo/redo
                            data.regions[i].context.pk = region.pk;
                        }.bind(this));
                }
            }
            if (data.lines && data.lines.length) {
                this.$parent.$emit(
                    'bulk_create:lines',
                    data.lines.map(l => {
                        return {
                            pk: l.pk,
                            baseline: l.baseline,
                            mask: l.mask,
                            region: l.region && l.region.context.pk || null
                        };
                    }),
                    function(newLines) {
                        for (let i=0; i<newLines.length; i++) {
                            let line = newLines[i];
                            // create a new line in case the event didn't come from the editor
                            if (createInEditor) {
                                let region = this.segmenter.regions.find(r=>r.context.pk==line.region);
                                this.segmenter.loadLine(line, region);
                            }
                            // update the segmenter pk
                            data.lines[i].context.pk = line.pk;
                        }
                    }.bind(this));
            }
        },
        bulkUpdate(data) {
            if (data.regions && data.regions.length) {
                for(let i=0; i<data.regions.length; i++) {
                    let region = data.regions[i];
                    this.$parent.$emit(
                        'update:region', {
                            pk: region.context.pk,
                            box: region.box,
                            type: region.type
                        },
                        function(region) {
                            let segmenterRegion = this.segmenter.regions.find(r=>r.context.pk==region.pk);
                            segmenterRegion.update(region.box);
                        }.bind(this)
                    );
                }
            }
            if (data.lines && data.lines.length) {
                this.$parent.$emit(
                    'bulk_update:lines',
                    data.lines.map(l => {
                        return {
                            pk: l.context.pk,
                            baseline: l.baseline,
                            mask: l.mask,
                            region: l.region && l.region.context.pk,
                            type: l.type
                        };
                    }),
                    function(updatedLines) {
                        for (let i=0; i<updatedLines.length; i++) {
                            let line = updatedLines[i];
                            let region = this.segmenter.regions.find(r=>r.context.pk==line.region) || null;
                            let segmenterLine = this.segmenter.lines.find(l=>l.context.pk==line.pk);
                            segmenterLine.update(line.baseline, line.mask, region, line.order);
                        }
                    }.bind(this)
                );
            }
        },
        bulkDelete(data) {
            if (data.regions && data.regions.length) {
                // regions have a bulk delete
                for(let i=0; i<data.regions.length; i++) {
                    this.$parent.$emit(
                        'delete:region',
                        data.regions[i].context.pk,
                        function(deletedRegionPk) {
                            let region = this.segmenter.regions.find(r=>r.context.pk==deletedRegionPk);
                            if (region) region.remove();
                        }.bind(this)
                    );
                }
            }
            if (data.lines && data.lines.length) {
                this.$parent.$emit(
                    'bulk_delete:lines',
                    data.lines.map(l=>l.context.pk),
                    function(deletedLines) {
                        this.segmenter.lines
                            .filter(l=> { return deletedLines.indexOf(l.context.pk) >= 0; })
                            .forEach(l=>{ l.remove(); });
                    }.bind(this)
                );
            }
        },

        extractPrevious(data) {
            // given modifications on lines/regions,
            // update data with a previous attribute containing the current state
            if (data.regions && data.regions.length) {
                data.regions.forEach(function(r) {
                    let region = this.part.regions.find(e=>e.pk==r.context.pk);
                    if (region) {
                        r.previous = {
                            context: r.context,
                            box: region && region.box.slice()  // copy the array
                        };
                    }
                }.bind(this));
            }
            if (data.lines && data.lines.length) {
                data.lines.forEach(function(l) {
                    let line = this.part.lines.find(e=>e.pk==l.context.pk);
                    if (line) {
                        l.previous = {
                            context: l.context,
                            baseline: line.baseline && line.baseline.slice(),
                            mask: line.mask && line.mask.slice(),
                            region: line.region && this.segmenter.regions.find(r=>r.context.pk==line.region) || null
                        };
                    }
                }.bind(this));
            }
        },

        processLines(ev) {
            ev.target.disabled = true;
            this.part.recalculateMasks();
        },

        /* History */
        undo() {
            this.undoManager.undo();
            this.refreshHistoryBtns();
        },
        redo() {
            this.undoManager.redo();
            this.refreshHistoryBtns();
        },
        refreshHistoryBtns() {
            if (this.undoManager.hasUndo()) this.$el.querySelector('#undo').disabled = false;
            else this.$el.querySelector('#undo').disabled = true;
            if (this.undoManager.hasRedo()) this.$el.querySelector('#redo').disabled = false;
            else this.$el.querySelector('#redo').disabled = true;
        }
    }
});
