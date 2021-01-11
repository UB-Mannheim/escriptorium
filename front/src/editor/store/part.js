import * as api from '../api'

// singleton!
export const partStore = {
    // need to set empty value for vue to watch them
    documentId: null,
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
            let type_ = line.typology && this.types.lines.find(t=>t.pk == line.typology);
            line.type = type_ && type_.name;
        }.bind(this));
        part.regions.forEach(function(reg) {
            let type_ = reg.typology && this.types.regions.find(t=>t.pk == reg.typology)
            reg.type = type_ && type_.name;
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

    loadTranscription (line, transcription) {
        let tr = line.transcriptions || {};
        if (transcription) {
            tr[transcription.transcription] = transcription;
            Vue.set(line, 'transcriptions', tr);
        }
    },

    // actions
    fetchPart(pk, callback) {
        this.pk = pk;
        this.fetchDocument(function() {
            api.retrieveDocumentPart(this.documentId, pk)
                .then(function(response) {
                    let data = response.data;
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
        api.retrieveDocument(this.documentId)
            .then(function(response) {
                let data = response.data;
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
            api.retrievePage(this.documentId, this.pk, transcription, page)
                .then(function(response) {
                    let data = response.data;
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
        let data = {
            content: lineTranscription.content,
            line: lineTranscription.line,
            transcription: lineTranscription.transcription
        }

        let pushContentAction = api.createContent;
        let params = [this.documentId, this.pk];
        if (lineTranscription.pk) {
            pushContentAction = api.updateContent
            params.push(lineTranscription.pk);
        }
        pushContentAction(...params, data)
            .then((response) => {
                let data = response.data;
                let line = this.lines.find(l=>l.pk == lineTranscription.line);
                this.loadTranscription(line, data);
                line.currentTrans = data;
            })
            .catch(function(error) {
                console.log('couldnt update transcription!', error);
            }.bind(this));
    },
    createLine(line, transcription, callback) {
        let data = {
            document_part: this.pk,
            baseline: line.baseline,
            mask: line.mask,
            region: line.region
        };
        api.createLine(this.documentId, this.pk, data)
            .then(function(response) {
                let newLine = response.data;
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
        lines.forEach(l=>l.document_part = this.pk);
        api.bulkCreateLines(this.documentId, this.pk, {lines: lines})
            .then(function(response) {
                let data = response.data;
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
        line.document_part = this.pk;
        api.updateLine(this.documentId, this.pk, line.pk, line)
            .then(function(response) {
                let data = response.data;
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
        let data = lines.map(function(l) {
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

        api.bulkUpdateLines(this.documentId, this.pk, {lines: data})
            .then(function(response) {
                let data = response.data;
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
        api.deleteLine(this.documentId, this.pk, linePk)
            .then(function(response) {
                let index = this.lines.findIndex(l=>l.pk==linePk);
                Vue.delete(this.part.lines, index);
                this.recalculateOrdering();
            }.bind(this))
            .catch(function(error) {
                console.log('couldnt delete line #', linePk)
            });
    },
    bulkDeleteLines(pks, callback) {
        api.bulkDeleteLines(this.documentId, this.pk, {lines: pks})
            .then(function(response) {
                let deletedLines = [];
                for (let i=0; i<pks.length; i++) {
                    let index = this.lines.findIndex(l=>l.pk==pks[i]);
                    if(index != -1) {
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
                const params = {}
                if (this.masksToRecalc.length > 0) params.only = this.masksToRecalc.toString();
                this.masksToRecalc = [];
                this.recalculateMasks(this.documentId, this.pk, {}, params)
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
                api.recalculateOrdering(this.documentId, this.pk, {})
                    .then(function(response) {
                        let data = response.data;
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
    rotate(angle, callback) {
        api.rotateDocumentPart(this.documentId, this.pk, {angle: angle})
            .then(function(response) {
                this.reload(callback);
            }.bind(this))
            .catch(function(error) {
                console.log('couldnt rotate!', error);
            });
    },

    createRegion(region, callback) {
        let type = region.type && this.types.regions.find(t=>t.name==region.type);
        let data = {
            document_part: this.pk,
            typology: type && type.pk || null,
            box: region.box
        };
        api.createRegion(this.documentId, this.pk, data)
            .then(function(response) {
                let data = response.data;
                this.regions.push(data);
                callback(data);
            }.bind(this))
            .catch(function(error) {
                console.log('couldnt create region', error)
            });
    },
    updateRegion(region, callback) {
        let type = region.type && this.types.regions.find(t=>t.name==region.type);
        let data = {
            document_part: this.pk,
            box: region.box,
            typology: type && type.pk || null
        };
        api.updateRegion(this.documentId, this.pk, region.pk, data)
            .then(function(response) {
                let data = response.data;
                let index = this.regions.findIndex(l=>l.pk==region.pk);
                this.regions[index].box = data.box;
                callback(data);
            }.bind(this))
            .catch(function(error) {
                console.log('couldnt update region', error)
            });
    },
    deleteRegion(regionPk, callback) {
        api.deleteRegion(this.documentId, this.pk, regionPk)
            .then(function(response) {
                let index = this.regions.findIndex(r=>r.pk==regionPk);
                callback(this.regions[index].pk);
                Vue.delete(this.regions, index);
            }.bind(this))
            .catch(function(error) {
                console.log('couldnt delete region #', regionPk, error);
            });
    },
    archiveTranscription(transPk) {
        api.archiveTranscription(this.documentId, transPk)
            .then(function(response) {
                let index = this.transcriptions.findIndex(t=>t.pk==transPk)
                Vue.delete(this.transcriptions, index);
            }.bind(this))
            .catch(function(error) {
                console.log('couldnt archive transcription #', transPk, error);
            });
    },
    bulkCreateLineTranscriptions(transcriptions, callback){
        let data = transcriptions.map(l=>{
            return {
                line : l.line,
                transcription : l.transcription,
                content : l.content
            }
        });

        api.bulkCreateLineTranscriptions(this.documentId, this.pk, {lines: data})
            .then(function(response) {
                let data = response.data;
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
        let data = transcriptions.map(l => {
            return {
                pk: l.pk,
                content: l.content,
                line : l.line,
                transcription : l.transcription
            };
        });

        api.bulkUpdateLineTranscriptions(this.documentId, this.pk, {lines: data})
            .then(function(response) {
                callback();
            })
            .catch(function(error) {
                console.log('couldnt update line', error)
            });
    },
    move(movedLines, callback){
        api.moveLines(this.documentId, this.pk, {"lines": movedLines})
            .then(function(response) {
                let data = response.data;
                for (let i=0; i<data.length; i++) {
                    let lineData = data[i];
                    let line = this.lines.find(function(l) {
                        return l.pk==lineData.pk;
                    });
                    if (line) {
                        line.order = lineData.order;
                    }
                }
                callback();
            }.bind(this)).catch(function(error) {
                console.log('couldnt recalculate order of line', error)
            });
    },

    reset() {
        // triggers delayed function immediately before the underlying data(pks) changes
        if (this.debouncedRecalculateMasks) {
            this.debouncedRecalculateMasks.flush();
        }
        if (this.debouncedRecalculateOrdering) {
            this.debouncedRecalculateOrdering.flush();
        }

        // note: keep the transcriptions
        this.loaded = false;
        this.pk = null;
        this.lines = [];
        this.regions = [];
        this.image = {};
    },

    getPrevious(cb) {
        if (this.loaded && this.previous) {
            this.reset();
            this.fetchPart(this.previous, cb);
        }
    },
    getNext(cb) {
        if (this.loaded && this.next) {
            this.reset();
            this.fetchPart(this.next, cb);
        }
    },
    reload(cb) {
        let pk = this.pk;
        this.reset();
        this.fetchPart(pk, cb);
    }
};
