const partStore = {
    // need to set empty value for vue to watch them
    pk: null,
    lines: [],
    regions: [],
    image: {},

    selectedTranscription: document.getElementById('document-transcriptions').value,
    masksToRecalc: [],

    // mutators
    load (part) {
        Object.assign(this, part);
    },
    changeTranscription(pk) {
        this.selectedTranscription = pk;
        this.fetchTranscriptions();
    },

    // helpers
    hasPrevious() { return this.loaded && this.previous !== null },
    hasNext() { return this.loaded && this.next !== null; },
    // properties
    get loaded() {
        return this.pk;
    },
    get hasMasks() {
        return this.lines.findIndex(l=>l.mask!=null) != -1;
    },

    // api
    getApiRoot(pk) {
        return '/api/documents/' + DOCUMENT_ID + '/parts/' + (pk?pk:this.pk) + '/';
    },

    loadTranscription (transcription) {
        // use Vue.set or the transcription won't be watched.
        let line = this.lines.find(l=>l.pk == transcription.line);
        Vue.set(line, 'transcription', transcription);
    },

    // actions
    fetch(pk) {
        let uri = this.getApiRoot(pk);
        fetch(uri)
            .then((response)=>response.json())
            .then(function(data) {
                this.load(data);
                this.fetchTranscriptions();
            }.bind(this))
            .catch(function(error) {
                console.log('couldnt fetch data!', error);
            });
    },

    fetchTranscriptions() {
        // first create a default transcription for every line
        this.lines.forEach(function(line) {
            this.loadTranscription({
                line: line.pk,
                transcription: this.selectedTranscription,
                content: '',
                versions: []
            });
        }.bind(this));

        //  then fetch all content page by page
        let fetchPage = function(page) {
            let uri = this.getApiRoot() + 'transcriptions/?transcription=' + this.selectedTranscription + '&page=' + page;
            fetch(uri)
                .then((response)=>response.json())
                .then(function(data) {
                    for (var i=0; i<data.results.length; i++) {
                        this.loadTranscription(data.results[i]);
                    }
                    if (data.next) fetchPage(page+1);
                }.bind(this));
        }.bind(this);
        fetchPage(1);
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

    createLine(line, callback) {
        let uri = this.getApiRoot() + 'lines/';
        data = {
            document_part: this.pk,
            baseline: line.baseline,
            mask: line.mask,
            region: line.region
        };
        this.push(uri, data, method="post")
            .then((response) => response.json())
            .then(function(data) {
                let newLine = data;
                newLine.transcription = {
                    line: newLine.pk,
                    transcription: this.selectedTranscription,
                    content: '',
                    versions: []
                };
                this.lines.push(newLine);
                this.recalculateOrdering();
                if (this.hasMasks) {
                    this.recalculateMasks();
                }
                callback(newLine);
            }.bind(this))
            .catch(function(error) {
                console.log('couldnt create line', error)
            });
    },
    bulkCreateLines(lines, callback) {
        let uri = this.getApiRoot() + 'lines/bulk_create/';
        lines.forEach(l=>l.document_part = this.pk);
        this.push(uri, {lines: lines}, method="post")
            .then((response) => response.json())
            .then(function(data) {
                let createdLines = [];
                for (let i=0; i<data.lines.length; i++) {
                    let l = data.lines[i];
                    let newLine = l;
                    newLine.transcription = {
                        line: newLine.pk,
                        transcription: this.selectedTranscription,
                        content: '',
                        versions: []
                    }
                    createdLines.push(newLine)
                    this.lines.push(newLine);
                }
                this.recalculateOrdering();
                if (this.hasMasks) {
                    this.recalculateMasks(createdLines.map(l=>l.pk));
                }
                callback(createdLines);
            }.bind(this))
            .catch(function(error) {
                console.log('couldnt create lines', error)
            });
    },
    updateLine(line, callback) {
        let uri = this.getApiRoot() + 'lines/' + line.pk + '/';
        line.document_part = this.pk;
        this.push(uri, line, method="put")
            .then((response) => response.json())
            .then(function(data) {
                let index = this.lines.findIndex(l=>l.pk==line.pk);
                this.lines[index].baseline = data.baseline;
                this.lines[index].mask = data.mask;
                callback(this.lines[index]);
            }.bind(this))
            .catch(function(error) {
                console.log('couldnt update line', error)
            });
    },
    bulkUpdateLines(lines, callback) {
        let uri = this.getApiRoot() + 'lines/bulk_update/';
        lines.forEach(l=>l.document_part = this.pk);
        this.push(uri, {lines: lines}, method="put")
            .then((response) => response.json())
            .then(function(data) {
                let updatedLines = [];
                for (let i=0; i<data.lines.length; i++) {

                    let lineData = data.lines[i];
                    let line = this.lines.find(function(l) {
                        return l.pk==lineData.pk;
                    });
                    if (line) {
                        line.baseline = lineData.baseline;
                        line.mask = lineData.mask;
                        line.region = lineData.region;
                        updatedLines.push(line);
                    }
                }
                if (this.hasMasks) {
                    this.recalculateMasks(updatedLines.map(l=>l.pk));
                }
                if (callback) callback(updatedLines);
            }.bind(this))
            .catch(function(error) {
                console.log('couldnt update line', error)
            });
    },
    deleteLine(linePk, callback) {
        let uri = this.getApiRoot() + 'lines/' + linePk + '/';
        this.push(uri, {}, method="delete")
            .then(function(data) {
                let index = this.lines.findIndex(l=>l.pk==linePk);
                Vue.delete(this.part.lines, index);
                this.recalculateOrdering();
            }.bind(this))
            .catch(function(error) {
                console.log('couldnt delete line #', linePk)
            });
    },
    bulkDeleteLines(pks, callback) {
        let uri = this.getApiRoot() + 'lines/bulk_delete/';
        this.push(uri, {lines: pks}, method="post")
            .then(function(data) {
                let deletedLines = [];
                for (let i=0; i<pks.length; i++) {
                    let index = this.lines.findIndex(l=>l.pk==pks[i]);
                    if(index) {
                        deletedLines.push(pks[i]);
                        Vue.delete(this.lines, index);
                    }
                }
                this.recalculateOrdering();
                if(callback) callback(deletedLines);
            }.bind(this))
            .catch(function(error) {
                console.log('couldnt bulk delete lines', error);
            });
    },
    recalculateMasks(only=[]) {
        this.masksToRecalc = _.uniq(this.masksToRecalc.concat(only));
        if (!this.debouncedRecalculateMasks) {
            // avoid calling this too often
            this.debouncedRecalculateMasks = _.debounce(function(only) {
                let uri = this.getApiRoot() + 'reset_masks/';
                if (this.masksToRecalc.length >0) uri += '?only=' + this.masksToRecalc.toString();
                this.masksToRecalc = [];
                this.push(uri, {}, method="post")
                    .then((response) => response.json())
                    .then(function(data) {
                        for (let i=0; i<data.lines.length; i++) {
                            let lineData = data.lines[i];
                            let line = this.lines.find(function(l) {
                                return l.pk==lineData.pk;
                            });
                            if (line) {
                                line.mask = lineData.mask;
                            }
                        }
                    }.bind(this))
                    .catch(function(error) {
                        console.log('couldnt recalculate masks!', error);
                    });
            }.bind(this), 2000);
        }
        this.debouncedRecalculateMasks(only);
    },
    recalculateOrdering() {
        if (!this.debouncedRecalculateOrdering) {
            // avoid calling this too often
            this.debouncedRecalculateOrdering = _.debounce(function() {
                let uri = this.getApiRoot() + 'recalculate_ordering/';
                this.push(uri, {}, method="post")
                    .then((response) => response.json())
                    .then(function(data) {
                        for (let i=0; i<data.lines.length; i++) {
                            let lineData = data.lines[i];
                            let line = this.lines.find(function(l) {
                                return l.pk==lineData.pk;
                            });
                            if (line) {
                                line.order = i;
                            }
                        }
                    }.bind(this))
                    .catch(function(error) {
                        console.log('couldnt recalculate ordering!', error);
                    });
            }.bind(this), 1000);
        }
        this.debouncedRecalculateOrdering();
    },

    createRegion(region, callback) {
        let uri = this.getApiRoot() + 'blocks/';
        data = {
            document_part: this.pk,
            box: region.box
        };
        this.push(uri, data, method="post")
            .then((response) => response.json())
            .then(function(data) {
                this.regions.push(data);
                callback(data);
            }.bind(this))
            .catch(function(error) {
                console.log('couldnt create region', error)
            });
    },
    updateRegion(region, callback) {
        let uri = this.getApiRoot() + 'blocks/' + region.pk + '/';
        data = {
            document_part: this.pk,
            box: region.box
        };
        this.push(uri, data, method="put")
            .then((response) => response.json())
            .then(function(data) {
                let index = this.regions.findIndex(l=>l.pk==region.pk);
                this.regions[index].box = data.box;
                callback(data);
            }.bind(this))
            .catch(function(error) {
                console.log('couldnt update region', error)
            });
    },
    deleteRegion(regionPk, callback) {
        let uri = this.getApiRoot() + 'blocks/' + regionPk + '/';
        this.push(uri, {}, method="delete")
            .then(function(data) {
                let index = this.regions.findIndex(r=>r.pk==regionPk);
                callback(this.regions[index].pk);
                Vue.delete(this.regions, index);
            }.bind(this))
            .catch(function(error) {
                console.log('couldnt delete region #', regionPk, error);
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
    bulkCreateLineTranscriptions(transcriptions,callback){
        let uri = this.getApiRoot() + 'transcriptions/bulk_create/';
        let data = transcriptions.map(l=>{
            return {
                line : l.line,
                transcription : l.transcription,
                content : l.content
            }
        });

        this.push(uri, {lines: data}, method="post").
            then((response) => response.json())
            .then((function (data) {
                callback();
                console.log('linetranscriptions created with success')

            })).catch(function(error) {
                console.log('couldnt create transcription lines', error)
            });


    },
    bulkUpdateLineTranscriptions(transcriptions, callback) {
        let uri = this.getApiRoot() + 'transcriptions/bulk_update/';
        let data = transcriptions.map(l => {
            return {
                pk: l.pk,
                content: l.content,
                line : l.line
            };
        });

        this.push(uri, {lines: data}, method="put")
            .then((response) => response.json())
            .then(function(data) {
                callback();
            })
            .catch(function(error) {
                console.log('couldnt update line', error)
            });
    },
    move(linePk,index,callback){
        let uri = this.getApiRoot() + 'lines/'+ linePk + '/move/';
        this.push(uri,{index : index},method="post")
            .then((response) =>response.json())
            .then(function (data) {
                callback();
            }).catch(function(error) {
                console.log('couldnt recalculate order of line', error)
            });

    },
    getPrevious() {
        if (this.loaded && this.previous) {
            this.fetch(this.previous);
        }
    },
    getNext() {
        if (this.loaded && this.next) {
            this.fetch(this.next);
        }
    }
};
