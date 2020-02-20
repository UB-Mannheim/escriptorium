var zoom = new WheelZoom();
// var undoManager = new UndoManager();

var partVM = new Vue({
    el: "#part-edit",
    delimiters: ["${","}"],
    data: {
        part: {
            name: "",
            filename: "",
            image: null
        },
        loaded: false,
        selectedTranscription: document.getElementById('document-transcriptions').value
    },
    components: {
        'sourcepanel': SourcePanel,
        'visupanel': VisuPanel
    },    
    mounted: function() {
        this.fetch();
    },
    computed: {
        imageSize: function() {
            return this.part.image.size[0]+'x'+this.part.image.size[1];
        }
    },
    watch: {
        selectedTranscription: function(newTrans, oldTrans) {
            this.loadTranscriptions();
        }
    },
    methods: {
        getApiRoot: function() {
            return '/api/documents/' + DOCUMENT_ID + '/parts/' + PART_ID + '/';
        },
        
        loadTranscriptions: function(transId) {
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
                            Vue.set(line, 'transcription', null);
                        }
                    }
                    if (data.next) getNext(page+1);
                }.bind(this));
            }.bind(this);
            getNext(1);
        },
        
        fetch: function() {
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
        
        getPrevious: function() {
            if (this.loaded && this.part.previous) {
                PART_ID = this.part.previous;
                this.fetch();
            }
        },
        getNext: function() {
            if (this.loaded && this.part.next) {
                PART_ID = this.part.next;
                this.fetch();
            }
        }
    }
});
