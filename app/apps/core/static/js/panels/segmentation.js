/*
TODO:
- list of regions / lines (?)
*/

class SegmentationPanel extends Panel {
    constructor ($panel, $tools, opened) {
        super($panel, $tools, opened);
        this.loaded = false;
        this.seeBlocks = true;
        this.seeLines = true;
        this.$img = $('img', this.$container);
        this.zoomTarget = zoom.register($('.zoom-container', this.$container).get(0), {map: true});
        this.segmenter = new Segmenter(this.$img.get(0), {
            delayInit:true,
            idField:'pk',
            defaultReadDirection: READ_DIRECTION
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
        this.segmenter.events.addEventListener('baseline-editor:delete-line', function(event) {
            let line = event.detail;
            this.remoteDelete('lines', line);
            this.pushHistory(
                function() {  // undo
                    line = this.segmenter.createLine(line.baseline, line.mask);
                    this.remoteSave('lines', line);
                }.bind(this),
                function() {  // redo
                    line.remove();
                    this.remoteDelete('lines', line);
                }.bind(this));
        }.bind(this));

        this.segmenter.events.addEventListener('baseline-editor:update-line', function(event) {
            let line = event.detail.line;
            let newdata = {baseline: line.baseline, mask: line.mask};
            let previousdata = event.detail.previous;
            this.remoteSave('lines', line);
            
            if(!line.context.pk) {
                // new line
                this.pushHistory(
                    function() {  // undo
                        line.remove();
                        this.remoteDelete('lines', line);
                    }.bind(this),
                    function() {  // redo
                        line = this.segmenter.createLine(line.baseline, line.mask);
                        this.remoteSave('lines', line);
                    }.bind(this)
                );
            } else {
                this.pushHistory(
                    function() {  //undo
                        line.update(previousdata.baseline, previousdata.mask);
                        this.remoteSave('lines', line);
                    }.bind(this),
                    function() {  // redo
                        line.update(newdata.baseline, newdata.mask);
                        this.remoteSave('lines', line);
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
            regions: this.part.regions
        });
        
        this.bindZoom();
    }
    
    load(part) {
        this.segmenter.empty();
        super.load(part);
        if (this.part.image.thumbnails && this.part.image.thumbnails.large) {
            this.$img.attr('src', this.part.image.thumbnails.large);
        } else {
            this.$img.attr('src', this.part.image.uri);
        }
        if (this.opened) {
            if (this.$img.get(0).complete) { this.init(); }
            else { this.$img.on('load', this.init.bind(this)); }
        }
        this.loaded = true;
    }

    onShow() {
        if (this.loaded) {
            if (this.$img.get(0).complete) { this.init(); }
            else { this.$img.on('load', this.init.bind(this)); }
        }
    }

    convertPolygon(poly, ratio) {
        if (poly === null) return null;
        return poly.map(pt => [Math.round(pt[0]*ratio),
                               Math.round(pt[1]*ratio)]);
    }
    
    remoteSave(type, obj) {
        var post = {document_part: this.part.pk};
        if (type=='lines') {
            post['baseline'] = JSON.stringify(obj.baseline);
            post['mask'] = JSON.stringify(obj.mask);
            post['block'] = this.block?this.block.pk:null; // todo
        } else if (type == 'blocks') {
            post['box'] = JSON.stringify(obj.polygon);
        }
        let uri = this.api + type + '/';
        let pk = obj.context.pk;
        if (pk) uri += pk+'/';
        var requestType = pk?'PUT':'POST';
        $.ajax({url: uri, type: requestType, data: post})
            .done($.proxy(function(data) {
                obj.context.pk = data.pk;
                if (type == 'lines') {
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
        let uri = this.api + type + '/' + obj.context.pk;
        $.ajax({url: uri, type:'DELETE'});
        if (type == 'lines' && panels['trans']) {
            let tl = panels['trans'].lines.find(l => l.pk==obj.context.pk);
            if (tl) tl.delete();
            panels['trans'].lines.splice(index, 1);
        }
    }
    
    refresh() {
        super.refresh();
        if (this.opened) {
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
