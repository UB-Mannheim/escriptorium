var partVM = new Vue({
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
        fullSizeImage: false
    },
    computed: {
        selectedTranscription: {
            get() { return this.part.selectedTranscription; },
            set(newValue) { this.part.changeTranscription(newValue); }
        },
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
                let target = {x: this.$el.clientWidth/this.openedPanels.length/2-this.zoom.pos.x,
                              y: this.$el.clientHeight/this.openedPanels.length/2-this.zoom.pos.y};
                this.zoom.zoomTo(target, parseFloat(newValue)-this.zoom.scale);
            }
        }
    },
    watch: {
        openedPanels(n, o) {
            // wait for css
            Vue.nextTick(function() {
                if(this.$refs.segPanel) this.$refs.segPanel.refresh();
                if(this.$refs.visuPanel) this.$refs.visuPanel.refresh();
            }.bind(this));
        },
        'part.pk': function(a) {
            // set the new url
            window.history.pushState({},"",
                document.location.href.replace(/(part\/)\d+(\/edit)/,
                                               '$1'+this.part.pk+'$2'));
            
            // set the 'image' tab btn to select the corresponding image
            var tabUrl = new URL($('#images-tab-link').attr('href'), window.location.origin);
            tabUrl.searchParams.set('select', this.part.pk);
            $('#images-tab-link').attr('href', tabUrl);
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
        this.part.fetch(PART_ID);
        
        // bind all events emited from panels and such
        this.$on('update:transcription', function(lineTranscription) {
            this.part.pushTranscription(lineTranscription);
        }.bind(this));
        this.$on('update:transcription:new-version', function(line) {
            this.part.pushVersion(line);
        }.bind(this));
        
        this.$on('create:line', function(line, cb) {
            this.part.createLine(line, cb);
        }.bind(this));
        this.$on('bulk_create:lines', function(line, cb) {
            this.part.bulkCreateLines(line, cb);
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

        this.$on('bulk_update:transcriptions', function(lines, cb) {
            this.part.bulkUpdateLineTranscriptions(lines, cb);
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
            }
        }.bind(this));

        let debounced = _.debounce(function() {  // avoid calling this too often
            if(this.$refs.segPanel) this.$refs.segPanel.refresh();
            if(this.$refs.visuPanel) this.$refs.visuPanel.refresh();
        }.bind(this), 200);
        window.addEventListener('resize', debounced);
        
        // load the full size image when we reach a scale > 1
        this.zoom.events.addEventListener('wheelzoom.updated', function(ev) {
            let ratio = ev.target.clientWidth / this.part.image.size[0];
            if (this.zoom.scale  * ratio > 1) {
                this.fullSizeImage = true;
            }
        }.bind(this));
    },
    methods: {
        resetZoom() {
            this.zoom.reset();
        },

        getPrevious(ev) { return this.part.getPrevious(); },
        getNext(ev) { return this.part.getNext(); },
        
        toggleSource() {
            this.show.source =! this.show.source;
            userProfile.set('source-panel', this.show.source);
        },
        toggleSegmentation() {
            this.show.segmentation =! this.show.segmentation;
            userProfile.set('segmentation-panel', this.show.segmentation);
        },
        toggleVisualisation() {
            this.show.visualisation =! this.show.visualisation;
            userProfile.set('visualisation-panel', this.show.visualisation);
        },
        toggleDiplomatic() {
            this.show.diplomatic =! this.show.diplomatic;
            userProfile.set('diplomatic-panel', this.show.diplomatic);
        }
    }
});
