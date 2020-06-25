// singleton!
const partStore = {
    // need to set empty value for vue to watch them
    loaded: false,
    pk: null,
    lines: [],
    regions: [],
    image: {},
    transcriptions: [],

    // internal
    masksToRecalc: [],

    // mutators
    load (part) {
        // for each line/region enrich the correct type depending on typology id
        part.lines.forEach(function(line) {
            line.type = line.typology && this.types.lines.find(t=>t.pk == line.typology).name;
        }.bind(this));
        part.regions.forEach(function(reg) {
            reg.type = reg.typology && this.types.regions.find(t=>t.pk == reg.typology).name;
        }.bind(this));

        // will trigger all bindings
        Object.assign(this, part);
        this.loaded = true;
    },

    // helpers
    hasPrevious() { return this.loaded && this.previous !== null },
    hasNext() { return this.loaded && this.next !== null; },
    // properties
    get hasMasks() {
        return this.lines.findIndex(l=>l.mask!=null) != -1;
    },

    // api
    getApiRoot() {
        return '/api/documents/' + DOCUMENT_ID + '/';
    },
    getApiPart(pk) {
        return this.getApiRoot() + 'parts/' + (pk?pk:this.pk) + '/';
    },

    loadTranscription (line, transcription) {
        tr = line.transcriptions || {};
        if (transcription) {
            tr[transcription.transcription] = transcription;
            Vue.set(line, 'transcriptions', tr);
        }
    },

    // actions
    fetchPart(pk, callback) {
        this.reset();
        this.pk = pk;
        this.fetchDocument(function() {
            let uri = this.getApiPart(pk);
            fetch(uri)
                .then((response)=>response.json())
                .then(function(data) {
                    this.load(data, callback);
                    if (callback) callback(data);
                }.bind(this))
                .catch(function(error) {
                    console.log('couldnt fetch part data!', error);
                });
        }.bind(this));
    },
    fetchDocument(callback) {
        if (this.transcriptions.length) {  // assuming there is always at least one
            if (callback) callback({
                'transcriptions': this.transcriptions,
                'types': this.types
            });
            return;
        }
        let uri = this.getApiRoot();
        fetch(uri)
            .then((response)=>response.json())
            .then(function(data) {
                this.transcriptions = data.transcriptions;
                this.types = {
                    'regions': data.valid_block_types,
                    'lines': data.valid_line_types
                };
                if (callback) callback(data);
            }.bind(this));
    },
    fetchContent(transcription, callback) {
        // first create a default transcription for every line
        this.lines.forEach(function(line) {
            this.loadTranscription(line, {
                line: line.pk,
                transcription: transcription,
                content: '',
                version_author: null,
                version_source: null,
                version_updated_at: null
            });
        }.bind(this));
        //  then fetch all content page by page
        let fetchPage = function(page) {
            let uri = this.getApiPart(this.pk) + 'transcriptions/?transcription=' + transcription + '&page=' + page;
            fetch(uri)
                .then((response)=>response.json())
                .then(function(data) {
                    for (var i=0; i<data.results.length; i++) {
                        let line = this.lines.find(l=>l.pk == data.results[i].line);
                        this.loadTranscription(line, data.results[i]);
                    }
                    if (data.next) fetchPage(page+1);
                    else if (callback) callback(data);
                }.bind(this));
        }.bind(this);
        fetchPage(1);
    },
    pushContent(lineTranscription) {
        let uri, method;
        let data = {
            content: lineTranscription.content,
            line: lineTranscription.line,
            transcription: lineTranscription.transcription
        }
        if (lineTranscription.pk) {
            uri = this.getApiPart() + 'transcriptions/' + lineTranscription.pk + '/';
            method = "put";
        } else {
            uri = this.getApiPart() + 'transcriptions/';
            method = "post";
        }
        this.push(uri, data, method=method)
            .then((response)=>response.json())
            .then((data) => {
                let line = this.lines.find(l=>l.pk == lineTranscription.line);
                this.loadTranscription(line, data);
                line.currentTrans = data;
            })
            .catch(function(error) {
                console.log('couldnt update transcription!', error);
            }.bind(this));
    },
    createLine(line, transcription, callback) {
        let uri = this.getApiPart() + 'lines/';
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
                newLine.currentTrans = {
                    line: newLine.pk,
                    transcription: transcription,
                    content: '',
                    versions: [],
                    version_author: '',
                    version_source: '',
                    version_updated_at: null
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
    bulkCreateLines(lines, transcription, callback) {
        let uri = this.getApiPart() + 'lines/bulk_create/';
        lines.forEach(l=>l.document_part = this.pk);
        this.push(uri, {lines: lines}, method="post")
            .then((response) => response.json())
            .then(function(data) {
                let createdLines = [];
                for (let i=0; i<data.lines.length; i++) {
                    let l = data.lines[i];
                    let newLine = l;
                    newLine.currentTrans = {
                        line: newLine.pk,
                        transcription: transcription,
                        content: '',
                        versions: [],
                        version_author: '',
                        version_source: '',
                        version_updated_at: null
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
        let uri = this.getApiPart() + 'lines/' + line.pk + '/';
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
        let uri = this.getApiPart() + 'lines/bulk_update/';

        data = lines.map(function(l) {
            let type  = l.type && this.types.lines.find(t=>t.name==l.type)
            return {
                pk: l.pk,
                document_part: this.pk,
                baseline: l.baseline,
                mask: l.mask,
                region: l.region,
                typology: type && type.pk || null
            };
        }.bind(this));

        this.push(uri, {lines: data}, method="put")
            .then((response) => response.json())
            .then(function(data) {
                let updatedLines = [];
                let updatedBaselines = [];
                for (let i=0; i<data.lines.length; i++) {
                    let lineData = data.lines[i];
                    let line = this.lines.find(function(l) {
                        return l.pk==lineData.pk;
                    });
                    if (line) {
                        if (!_.isEqual(line.baseline, lineData.baseline)) {
                            updatedBaselines.push(line)
                        }
                        line.baseline = lineData.baseline;
                        line.mask = lineData.mask;
                        line.region = lineData.region;
                        updatedLines.push(line);
                    }
                }
                if (this.hasMasks && updatedBaselines.length) {
                    this.recalculateMasks(updatedBaselines.map(l=>l.pk));
                }
                if (callback) callback(updatedLines);
            }.bind(this))
            .catch(function(error) {
                console.log('couldnt update line', error)
            });
    },
    deleteLine(linePk, callback) {
        let uri = this.getApiPart() + 'lines/' + linePk + '/';
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
        let uri = this.getApiPart() + 'lines/bulk_delete/';
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
                let uri = this.getApiPart() + 'reset_masks/';
                if (this.masksToRecalc.length >0) uri += '?only=' + this.masksToRecalc.toString();
                this.masksToRecalc = [];
                this.push(uri, {}, method="post")
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
                let uri = this.getApiPart() + 'recalculate_ordering/';
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
        let uri = this.getApiPart() + 'blocks/';
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
        let uri = this.getApiPart() + 'blocks/' + region.pk + '/';
        let type = region.type && this.types.regions.find(t=>t.name==region.type);
        data = {
            document_part: this.pk,
            box: region.box,
            typology: type && type.pk || null
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
        let uri = this.getApiPart() + 'blocks/' + regionPk + '/';
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
    archiveTranscription(transPk) {
        let uri = this.getApiRoot() + 'transcriptions/' + transPk + '/';
        this.push(uri, {}, method="delete")
            .then(function(data) {
                let index = this.transcriptions.findIndex(t=>t.pk==transPk)
                Vue.delete(this.transcriptions, index);
            }.bind(this))
            .catch(function(error) {
                console.log('couldnt archive transcription #', transPk, error);
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
    bulkCreateLineTranscriptions(transcriptions, callback){
        let uri = this.getApiPart() + 'transcriptions/bulk_create/';
        let data = transcriptions.map(l=>{
            return {
                line : l.line,
                transcription : l.transcription,
                content : l.content
            }
        });

        this.push(uri, {lines: data}, method="post")
            .then((response) => response.json())
            .then(function (data) {
                // update line.transcriptions pks
                for (let i=0; i<data.lines.length; i++) {
                    let lineTrans = data.lines[i];
                    let line = this.lines.find(l=>l.pk == lineTrans.line);
                    line.currentTrans.pk = lineTrans.pk;
                }
                callback();
            }.bind(this))
            .catch(function(error) {
                console.log('couldnt create transcription lines', error)
            });
    },
    bulkUpdateLineTranscriptions(transcriptions, callback) {
        let uri = this.getApiPart() + 'transcriptions/bulk_update/';
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

    reset() {
        // note: keep the transcriptions
        this.loaded = false;
        this.pk = null;
        this.lines = [];
        this.regions = [];
        this.image = {};
    },

    getPrevious(cb) {
        if (this.loaded && this.previous) {
            this.fetchPart(this.previous, cb);
        }
    },
    getNext(cb) {
        if (this.loaded && this.next) {
            this.fetchPart(this.next, cb);
        }
    }
};
