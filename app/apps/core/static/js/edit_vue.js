
// var undoManager = new UndoManager();

var partVM = new Vue({
    el: "#part-edit",
    delimiters: ["${","}"],
    data: {
        part: {
            name: "",
            filename: "",
            image: null,
            lines: []
        },
        loaded: false,
        selectedTranscription: document.getElementById('document-transcriptions').value,
        zoom: new WheelZoom()
    },
    components: {
        'sourcepanel': SourcePanel,
        'visupanel': VisuPanel
    },
    mounted() {
        this.fetch();
        this.$on('update:transcription', function(lineTranscription) {
            this.pushTranscription(lineTranscription);
        }.bind(this));
    },
    computed: {
        imageSize() {
            return this.part.image.size[0]+'x'+this.part.image.size[1];
        },
        zoomScale: {
            get() {
                return this.zoom.scale || 1;
            },
            set(newValue) {
                // TODO: divide by number of openent panels
                let target = {x: this.$el.clientWidth/2/2-this.zoom.pos.x,
                              y: this.$el.clientHeight/2/2-this.zoom.pos.y};
                this.zoom.zoomTo(target, parseFloat(newValue)-this.zoom.scale);
            }
        }
    },
    watch: {
        selectedTranscription(newTrans, oldTrans) {
            this.loadTranscriptions();
        }
    },
    methods: {
        resetZoom() {
            this.zoom.reset();
        },
        getApiRoot() {
            return '/api/documents/' + DOCUMENT_ID + '/parts/' + PART_ID + '/';
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
            fetch(uri, {
                method: method,
                credentials: "same-origin",
                headers: {
                    "X-CSRFToken": Cookies.get("csrftoken"),
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(lineTranscription)
            })
            .then( (response) => { 
                console.log(response);
            });
        },
        
        loadTranscriptions(transId) {
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
                            Vue.set(line, 'transcription', {
                                line: line.pk,
                                transcription: this.selectedTranscription,
                                content: ''
                            });
                        }
                    }
                    if (data.next) getNext(page+1);
                }.bind(this));
            }.bind(this);
            getNext(1);
        },
        
        fetch() {
            fetch(this.getApiRoot())
             .then((response)=>response.json())
             .then(function(data) {
                 this.part = data;
                 this.loaded = true;
                 this.loadTranscriptions();
             }.bind(this))
             .catch(function(response, data) {
                console.log('damn');
             }.bind(this));
        },
        
        getPrevious() {
            if (this.loaded && this.part.previous) {
                PART_ID = this.part.previous;
                this.fetch();
            }
        },
        getNext() {
            if (this.loaded && this.part.next) {
                PART_ID = this.part.next;
                this.fetch();
            }
        }
    }
});
