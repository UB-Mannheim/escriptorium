// TODO: use vuex for undo/redo?
// var undoManager = new UndoManager();

var partVM = new Vue({
    el: "#part-edit",
    delimiters: ["${","}"],
    data: {
        part: null,
        selectedTranscription: document.getElementById('document-transcriptions').value,
        zoom: new WheelZoom(),
        show: {
            source: userProfile.get('source-panel'),
            segmentation: userProfile.get('segmentation-panel'),
            visualisation: userProfile.get('visualisation-panel')
        },
        blockShortcuts: false
    },
    components: {
        'sourcepanel': SourcePanel,
        'segmentationpanel': SegPanel,
        'visupanel': VisuPanel
    },
    created() {
        this.fetch();
        // bind all events emited from panels and such
        this.$on('update:transcription', function(lineTranscription) {
            this.pushTranscription(lineTranscription);
        }.bind(this));
        this.$on('update:transcription:new-version', function(line) {
            this.pushVersion(line);
        }.bind(this));
        
        this.$on('create:line', function(line, cb) {
            this.createLine(line, cb);
        }.bind(this));
        this.$on('update:line', function(line, cb) {
            this.updateLine(line, cb);
        }.bind(this));
        this.$on('delete:line', function(linePk, cb) {
            this.deleteLine(linePk, cb);
        }.bind(this));

        this.$on('create:region', function(region, cb) {
            this.createRegion(region, cb);
        }.bind(this));
        this.$on('update:region', function(region, cb) {
            this.updateRegion(region, cb);
        }.bind(this));
        this.$on('delete:region', function(regionPk, cb) {
            this.deleteRegion(regionPk, cb);
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
                let target = {x: this.$el.clientWidth/this.openedPanels.length/2-this.zoom.pos.x,
                              y: this.$el.clientHeight/this.openedPanels.length/2-this.zoom.pos.y};
                this.zoom.zoomTo(target, parseFloat(newValue)-this.zoom.scale);
            }
        }
    },
    watch: {
        selectedTranscription(newTrans, oldTrans) {
            this.loadTranscriptions();
        },
        openedPanels(n, o) {
            // wait for css
            Vue.nextTick(function() {
                if(this.$refs.segPanel) this.$refs.segPanel.refresh();
                if(this.$refs.visuPanel) this.$refs.visuPanel.refresh();
            }.bind(this));
        }
    },
    methods: {
        resetZoom() {
            this.zoom.reset();
        },
        getApiRoot() {
            return '/api/documents/' + DOCUMENT_ID + '/parts/' + PART_ID + '/';
        },
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
        
        pushVersion(line) {
            if(!line.transcription.pk) return;
            uri = this.getApiRoot() + 'transcriptions/' + line.transcription.pk + '/new_version/';
            this.push(uri, {}, method='post')
                .then((response)=>response.json())
                .then((data) => {
                    line.transcription.versions.splice(0, 0, data);
                })
                .catch(function(error) {
                    console.log('couldnt save transcription state!', error);
                }.bind(this));
        },
        
        pushTranscription(lineTranscription) {
            let uri, method;
            if (lineTranscription.pk) {
                uri = this.getApiRoot() + 'transcriptions/' + lineTranscription.pk + '/';
                method = "put";
            } else {
                uri = this.getApiRoot() + 'transcriptions/';
                method = "post";
            }
            this.push(uri, lineTranscription, method=method)
            .then((response)=>response.json())
            .then((data) => {
                lineTranscription.pk = data.pk;
                lineTranscription.content = data.content;
                lineTranscription.versions = data.versions;
            })
            .catch(function(error) {
                console.log('couldnt update transcription!', error);
            }.bind(this));
        },
        
        loadTranscriptions() {
            let getNext = function(page) {
                let uri = this.getApiRoot() + 'transcriptions/?transcription='+this.selectedTranscription+'&page=' + page;
                fetch(uri)
                .then((response)=>response.json())
                .then(function(data) {
                    for (var i=0; i<this.part.lines.length; i++) {
                        let line = this.part.lines[i];
                        let lt = data.results.find(l => l.line == line.pk);
                        if (lt !== undefined) {
                            // use Vue.set or the transcription won't be watched.
                            Vue.set(line, 'transcription', lt);
                        } else {
                            // create an empty transcription
                            Vue.set(line, 'transcription', {
                                line: line.pk,
                                transcription: this.selectedTranscription,
                                content: '',
                                versions: []
                            });
                        }
                    }
                    if (data.next) getNext(page+1);
                }.bind(this));
            }.bind(this);
            getNext(1);
        },

        createLine(line, callback) {
            let uri = this.getApiRoot() + 'lines/';
            data = {
                document_part: this.part.pk,
                baseline: line.baseline,
                mask: line.mask,
                block: line.region
            };
            this.push(uri, data, method="post")
                .then((response) => response.json())
                .then(function(data) {
                    this.part.lines.push(data);
                    callback(data);
                }.bind(this))
                .catch(function(error) {
                    console.log('couldnt create line', error)
                });
        },
        updateLine(line, callback) {
            let uri = this.getApiRoot() + 'lines/' + line.pk + '/';
            data = {
                document_part: this.part.pk,
                baseline: line.baseline,
                mask: line.mask,
                block: line.region
            };
            this.push(uri, data, method="put")
                .then((response) => response.json())
                .then(function(data) {
                    let index = this.part.lines.findIndex(l=>l.pk==line.pk);
                    this.part.lines[index].baseline = data.baseline;
                    this.part.lines[index].mask = data.mask;
                }.bind(this))
                .catch(function(error) {
                    console.log('couldnt update line', error)
                });
        },
        deleteLine(linePk, callback) {
            let uri = this.getApiRoot() + 'lines/' + linePk;
            this.push(uri, {}, method="delete")
                .then(function(data) {
                    let index = this.part.lines.findIndex(l=>l.pk==linePk);
                    Vue.delete(this.part.lines, index);
                }.bind(this))
                .catch(function(error) {
                    console.log('couldnt delete line #', linePk)
                });
        },

        createRegion(region, callback) {
            let uri = this.getApiRoot() + 'blocks/';
            data = {
                document_part: this.part.pk,
                box: region.polygon
            };
            this.push(uri, data, method="post")
                .then((response) => response.json())
                .then(function(data) {
                    this.part.blocks.push(data);
                    callback(data);
                }.bind(this))
                .catch(function(error) {
                    console.log('couldnt create region', error)
                });
        },
        updateRegion(region, callback) {
            let uri = this.getApiRoot() + 'blocks/' + region.pk + '/';
            data = {
                document_part: this.part.pk,
                box: region.polygon
            };
            this.push(uri, data, method="put")
                .then((response) => response.json())
                .then(function(data) {
                    let index = this.part.blocks.findIndex(l=>l.pk==region.pk);
                    this.part.blocks[index].box = data.polygon;
                }.bind(this))
                .catch(function(error) {
                    console.log('couldnt update region', error)
                });
        },
        deleteRegion(regionPk, callback) {
            let uri = this.getApiRoot() + 'regions/' + regionPk;
            this.push(uri, {}, method="delete")
                .then(function(data) {
                    let index = this.part.blocks.findIndex(b=>b.pk==regionPk);
                    Vue.delete(this.part.blocks, index);
                }.bind(this))
                .catch(function(error) {
                    console.log('couldnt delete region #', regionPk)
                });
        },

        push(uri, data, method="post") {
            return fetch(uri, {
                method: method,
                credentials: "same-origin",
                headers: {
                    "X-CSRFToken": Cookies.get("csrftoken"),
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });    
        },
            
        fetch() {
            fetch(this.getApiRoot())
             .then((response)=>response.json())
             .then(function(data) {
                 this.part = data;
                 this.loadTranscriptions();
             }.bind(this))
                .catch(function(response, data) {
                    console.log('couldnt fetch data!');
             }.bind(this));
        },
        hasPrevious() { return this.part && this.part.previous !== null; },
        hasNext() { return this.part && this.part.next !== null; },
        getPrevious() {
            if (this.part && this.part.previous) {
                PART_ID = this.part.previous;
                this.fetch();
            }
        },
        getNext() {
            if (this.part && this.part.next) {
                PART_ID = this.part.next;
                this.fetch();
            }
        }
    }
});
