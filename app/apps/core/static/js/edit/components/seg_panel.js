/* 
Baseline editor panel (or segmentation panel)
*/

const SegPanel = BasePanel.extend({
    data() { return {
        colorMode: 'color'  //  color - binary - grayscale
    };},
    mounted() {
        // wait for the element to be rendered
        Vue.nextTick(function() {
            this.$parent.zoom.register(this.$el.querySelector('#seg-zoom-container'),
                                       {map: true});
            let beSettings = userProfile.get('baseline-editor') || {};
            this.$img = this.$el.querySelector('img');
            this.segmenter = new Segmenter(this.$img, {
                delayInit:true,
                idField:'pk',
                defaultTextDirection: TEXT_DIRECTION.slice(-2),
                baselinesColor: beSettings['color-baselines'] || null,
                evenMasksColor: beSettings['color-even-masks'] || null,
                oddMasksColor: beSettings['color-odd-masks'] || null,
                directionHintColor: beSettings['color-directions'] || null,
                regionColor: beSettings['color-regions'] || null
            });
            // we need to move the baseline editor canvas up one tag so that it doesn't get caught by wheelzoom.
            let canvas = this.segmenter.canvas;
            canvas.parentNode.parentNode.appendChild(canvas);

            // already mounted with a part = opening the panel after page load
            if (this.part.loaded) {
                this.onShow();
            }
            this.segmenter.events.addEventListener('baseline-editor:settings', function(ev) {
                let settings = userProfile.get('baseline-editor') || {};
                settings[event.detail.name] = event.detail.value;
                userProfile.set('baseline-editor', settings);
            });
            this.segmenter.events.addEventListener('baseline-editor:delete', function(ev) {
                let data = ev.detail;
                this.$parent.$emit('bulk_delete:regions', data.regions);
                this.$parent.$emit('bulk_delete:lines', data.lines);
            }.bind(this));
            this.segmenter.events.addEventListener('baseline-editor:update', function(ev) {
                let data = ev.detail;
                if (data.objType == 'region') {
                    if (data.obj.context.pk) {
                        this.$parent.$emit('update:region', {
                            pk: data.obj.context.pk,
                            polygon: data.obj.polygon
                        });
                    } else {
                        this.$parent.$emit('create:region', {
                            polygon: data.obj.polygon
                        }, function(resp) {
                            // callback, update the pk
                            data.obj.context.pk = resp.pk;
                        });
                    }
                } else {
                    if (data.obj.context.pk) {
                        this.$parent.$emit('update:line', {
                            pk: data.obj.context.pk,
                            baseline: data.obj.baseline,
                            mask: data.obj.mask,
                            region: data.obj.region
                        });
                    } else {
                        this.$parent.$emit('create:line', {
                            baseline: data.obj.baseline,
                            mask: data.obj.mask,
                            region: data.obj.region
                        }, function(resp) {
                            // callback from http request, update the pk
                            data.obj.context.pk = resp.pk;
                        });
                    }                    
                }                
            }.bind(this));
        }.bind(this));
    },
    computed: {
        hasBinaryColor() {
            return this.part.loaded && this.part.bw_image !== null;
        },

        // overrides imageSrc to deal with color modes
        imageSrcBin() {
            return (
                this.part.loaded && (
                    (this.colorMode == 'binary'
                     && this.part.bw_image
                     && this.part.bw_image.uri)
                        || this.imageSrc
                )
            );
        }
    },
    updated() {
        if (this.part.loaded) {
            if (this.colorMode !== 'binary' && !this.hasBinaryColor) {
                this.colorMode = 'color';
            }
            this.onShow();
        }
    },
    methods: {
        toggleBinary(ev) {
            if (this.colorMode == 'color') this.colorMode = 'binary';
            else this.colorMode = 'color';
        },
        onShow() {
            Vue.nextTick(function() {
                // the baseline editor needs to wait for the image to be fully loaded
                if (this.$img.complete) {
                    this.initSegmenter();
                } else {
                    this.$img.addEventListener('load', this.initSegmenter.bind(this), {once: true});
                }
                this.updateView();
            }.bind(this));
        },
        initSegmenter() {
            this.segmenter.empty();
            // we use a thumbnail so its size might not be the same as advertised in the api
            this.segmenter.scale = this.$img.naturalWidth / this.part.image.size[0];
            if (!this.segmenter.loaded) {
                this.segmenter.init();

                // simulates wheelzoom for canvas
                var zoom = this.$parent.zoom;
                zoom.events.addEventListener('wheelzoom.updated', function(e) {
                    
                    this.updateView();
                }.bind(this));
            } else {
                this.segmenter.refresh();
            }
            
            let regionMap = {};
            for (let i in this.part.blocks) {
                let region = this.part.blocks[i];
                regionMap[region.pk] = this.segmenter.load_region(region);
            }
            for (let i in this.part.lines) {
                let line = this.part.lines[i];
                this.segmenter.load_line(line, regionMap[line.block]);
            }

            // recalculate average line heights for lines without masks
            this.segmenter.resetLineHeights();
        },
        updateView() {
            // might not be mounted yet
            if (this.segmenter && this.$el.clientWidth) {
                var zoom = this.$parent.zoom;
                this.segmenter.canvas.style.top = zoom.pos.y + 'px';
                this.segmenter.canvas.style.left = zoom.pos.x + 'px';
                this.segmenter.refresh();
            }
        }
    }
});
