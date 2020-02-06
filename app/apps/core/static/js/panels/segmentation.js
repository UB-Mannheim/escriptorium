/*
TODO:
- list of regions / lines (?)
*/

class SegmentationPanel extends Panel {
    constructor ($panel, $tools, opened) {
        super($panel, $tools, opened);
        this.loading = false;
        this.loaded = false;
        this.seeBlocks = true;
        this.seeLines = true;
        this.$img = $('img', this.$container);
        this.colorMode = 'color';
        this.zoomTarget = zoom.register($('.zoom-container', this.$container).get(0), {map: true});
        this.segmenter = new Segmenter(this.$img.get(0), {
            delayInit:true,
            idField:'pk',
            defaultTextDirection: TEXT_DIRECTION.slice(-2)
        });
        // we need to move the baseline editor canvas up one block so that it doesn't get caught by wheelzoom.
        let canvas = this.segmenter.canvas;
        canvas.parentNode.parentNode.appendChild(canvas);
        
        this.resetMasksBtn = document.querySelector('#reset-masks');
        
        this.bindEditorEvents();
        
        let undoBtn = document.querySelector('button#undo');
        let redoBtn = document.querySelector('button#redo');
        if (undoBtn) undoBtn.addEventListener('click', function(ev) {
            undoManager.undo();
            this.updateHistoryBtns();
        }.bind(this));
        if (redoBtn) redoBtn.addEventListener('click', function(ev) {
            undoManager.redo();
            this.updateHistoryBtns();
        }.bind(this));
        
        this.toggleBinaryBtn = document.querySelector('button#toggle-binary');
        this.toggleBinaryBtn.addEventListener('click', function(ev) {
            this.toggleBinaryBtn.classList.toggle('btn-info');
            this.toggleBinaryBtn.classList.toggle('btn-success');

            if (this.colorMode == 'color') this.colorMode = 'binary';
            else this.colorMode = 'color';
            if (this.loaded) {
                let src = this.getImgSrcUri();
                preloadImage(src, function() {
                    this.$img.attr('src', src);
                    this.refresh();
                }.bind(this));
            }
        }.bind(this));
                
        document.addEventListener('keyup', function(event) {
            if (event.ctrlKey && event.keyCode == 90) {  // Ctrl+Z -> Undo
                undoManager.undo();
                this.updateHistoryBtns();
            } else if (event.ctrlKey && event.keyCode == 89) {  // Ctrl+Y -> Redo
                undoManager.redo();
                this.updateHistoryBtns();
            }
        }.bind(this));
    }

    pushHistory(undo, redo) {
        undoManager.add({undo:undo, redo:redo});
        this.updateHistoryBtns();
    }

    updateHistoryBtns() {
        let undoBtn = document.querySelector('button#undo');
        let redoBtn = document.querySelector('button#redo');
        
        if (undoManager.hasUndo()) undoBtn.disabled = false;
        else undoBtn.disabled = true;
        if (undoManager.hasRedo()) redoBtn.disabled = false;
        else redoBtn.disabled = true;
    }
    
    bindEditorEvents() {
        this.segmenter.events.addEventListener('baseline-editor:delete', function(event) {
            let obj = event.detail.obj, objType = event.detail.objType;
            this.remoteDelete(objType, obj);
            
            this.pushHistory(
                function() {  // undo
                    if (objType == 'line') {
                        obj = this.segmenter.createLine(null, obj.baseline, obj.mask);
                    } else if (objType == 'region'){
                        obj = this.segmenter.createRegion(obj.polygon);
                    }
                    this.remoteSave(objType, obj);
                }.bind(this),
                function() {  // redo
                    obj.remove();
                    this.remoteDelete(objType, obj);
                }.bind(this));
        }.bind(this));

        this.segmenter.events.addEventListener('baseline-editor:update', function(event) {
            let obj = event.detail.obj, objType = event.detail.objType;
            // let newdata = {baseline: line.baseline, mask: line.mask};
            let previousdata = event.detail.previous;
            this.remoteSave(objType, obj);
            
            if(!obj.context.pk) {
                // new line or region
                this.pushHistory(
                    function() {  // undo
                        obj.remove();
                        this.remoteDelete(objType, obj);
                    }.bind(this),
                    function() {  // redo
                        if (objType == 'line') {
                            obj = this.segmenter.createLine(null, obj.baseline, obj.mask);
                        } else if (objType == 'region') {
                            obj = this.segmenter.createRegion(obj.polygon);
                        }
                        this.remoteSave(objType, obj);
                    }.bind(this)
                );
            } else {
                this.pushHistory(
                    function() {  //undo
                        if (objType == 'line') {
                            obj.update(previousdata.baseline, previousdata.mask);
                        } else if (objType == 'region') {
                            obj.update(previousdata.polygon);
                        }
                        this.remoteSave(objType, obj);
                    }.bind(this),
                    function() {  // redo
                        if (objType == 'line') {
                            obj.update(obj.baseline, obj.mask);
                        } else if (objType == 'region') {
                            obj.update(obj.polygon);
                        }
                        this.remoteSave(objType, obj);
                    }.bind(this)
                );
            }
        }.bind(this));
        
        // avoid triggering keybindings events when not using the baseline segmenter
        this.segmenter.disableBindings = true;
        this.$panel.on('mouseover', function(e) {
            this.segmenter.disableBindings = false;
        }.bind(this));
        this.$panel.on('mouseout', function(e) {
            this.segmenter.disableBindings = true;
        }.bind(this));

        this.resetMasksBtn.addEventListener('click', function(ev) {
            let uri = this.api + 'reset_masks/';
            this.resetMasksBtn.disabled=true;
            $.ajax({url: uri, type: 'POST'})
                .done(function(data) {
                    if (data.lines) {
                        for (let i=0; i<data.lines.length; i++) {
                            // update segmentation panel
                            let line = this.segmenter.lines.find(l => l.context.pk==data.lines[i].id);
                            if (line) { line.update(false, data.lines[i].mask); }
                            // update translation panel
                            var tl = panels['trans'].lines.find(l => l.pk==data.lines[i].id);
                            if (tl) { tl.update(data.lines[i]); }
                        }
                    }
                }.bind(this))
                .fail(function(e) { alert(e); })
                .always(function(e) { this.resetMasksBtn.disabled=false; }.bind(this));
        }.bind(this));
    }
    
    init() {
        // we use a thumbnail so its size might not be the same as advertised in the api
        let ratio = this.$img.get(0).naturalWidth / this.part.image.size[0];
        this.segmenter.scale = ratio;
        this.segmenter.init();
        
        this.segmenter.load({
            lines: this.part.lines,
            regions: this.part.blocks
        });
        
        this.bindZoom();
        this.loading = false;
    }

    getImgSrcUri() {
        if (this.colorMode == 'binary' && this.part.bw_image) {
            return this.part.bw_image.uri;
        } else {
            if (this.part.image.thumbnails && this.part.image.thumbnails.large && !fullSizeImgLoaded) {
                return this.part.image.thumbnails.large;
            } else {
                return this.part.image.uri;
            }
        }
    }
    
    load(part) {
        this.loaded = false;
        this.segmenter.empty();
        super.load(part);
        this.$img.attr('src', this.getImgSrcUri());
        if (this.part.bw_image) this.toggleBinaryBtn.classList.remove('hide');
        else this.toggleBinaryBtn.classList.add('hide');
        if (this.opened) {
            this.loading = true;
            if (this.$img.get(0).complete) { this.init(); }
            else { this.$img.one('load', this.init.bind(this)); }
        } else {
            this.loading = false;
        }
        this.loaded = true;
    }

    onShow() {
        if (this.loaded && !this.loading) {
            this.loading = true;
            if (this.$img.get(0).complete) { this.init(); }
            else { this.$img.one('load', this.init.bind(this)); }
        }
    }

    convertPolygon(poly, ratio) {
        if (poly === null) return null;
        return poly.map(pt => [Math.round(pt[0]*ratio),
                               Math.round(pt[1]*ratio)]);
    }
    
    remoteSave(type, obj) {
        var uri, post = {document_part: this.part.pk};
        if (type=='line') {
            post['baseline'] = JSON.stringify(obj.baseline);
            post['mask'] = JSON.stringify(obj.mask);
            post['block'] = JSON.stringify(obj.region.context.pk);
            uri = this.api + 'lines' + '/';
        } else if (type == 'region') {
            post['box'] = JSON.stringify(obj.polygon);
            uri = this.api + 'blocks' + '/';
        }
        
        let pk = obj.context.pk;
        if (pk) uri += pk+'/';
        var requestType = pk?'PUT':'POST';
        $.ajax({url: uri, type: requestType, data: post})
            .done($.proxy(function(data) {
                obj.context.pk = data.pk;
                if (type == 'line') {
                    obj.update(data.baseline, data.mask);
                    /* create corresponding transcription line */
                    if (panels['trans']) {
                        if (!pk) {
                            panels['trans'].addLine(data);
                        } else {
                            var tl = panels['trans'].lines.find(l => l.pk==pk);
                            if (tl) { tl.update(data); }
                        }
                    }
                } else if (type == 'regions') {
                    obj.update(data.polygon);
                }
            }, this))
            .fail(function(data){
                alert("Couldn't save block:", data);
            });
    }

    remoteDelete(type, obj) {
        let uri;
        if (type == 'line') {
            uri = this.api + 'lines/' + obj.context.pk;
        } else {
            uri = this.api + 'blocks/' + obj.context.pk;
        }
        $.ajax({url: uri, type:'DELETE'});
        if (type == 'line' && panels['trans']) {
            let tl = panels['trans'].lines.find(l => l.pk==obj.context.pk);
            if (tl) tl.delete();
            panels['trans'].lines.splice(index, 1);
        }
    }
    
    refresh() {
        super.refresh();
        if (this.opened) {
            let ratio = this.$img.get(0).naturalWidth / this.part.image.size[0];
            this.segmenter.scale = ratio;
            this.segmenter.refresh();
        }
    }
    
    reset() {
        super.reset();
        this.segmenter.reset();
    }
    
    bindZoom() {
        // simulates wheelzoom for canvas
        var img = this.$img.get(0);
        zoom.events.addEventListener('wheelzoom.updated', function(e) {
            if (!this.opened) return;
            this.segmenter.canvas.style.top = zoom.pos.y + 'px';
            this.segmenter.canvas.style.left = zoom.pos.x + 'px';
            if (e.detail && e.detail.scale) {
                this.segmenter.refresh();
            }
        }.bind(this));
    }
}
