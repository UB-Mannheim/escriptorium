/*
TODO:
- help
- list of regions / lines (?)
*/

class SegmentationPanel extends Panel {
    constructor ($panel, $tools, opened) {
        super($panel, $tools, opened);
        this.seeBlocks = true;
        this.seeLines = true;
        this.$img = $('img', this.$container);
        this.zoomTarget = zoom.register($('.zoom-container', this.$container).get(0), {map: true});
        this.segmenter = new Segmenter(this.$img.get(0), {delayInit:true, idField:'pk'});
        // we need to move the baseline editor canvas up one block so that it doesn't get caught by wheelzoom.
        let canvas = this.segmenter.canvas;
        canvas.parentNode.parentNode.appendChild(canvas);

        this.bindEditorEvents();

        let undoBtn = document.querySelector('button#undo');
        let redoBtn = document.querySelector('button#redo');
        undoBtn.addEventListener('click', function(ev) {
            undoManager.undo();
            this.updateHistoryBtns();
        }.bind(this));
        redoBtn.addEventListener('click', function(ev) {
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
        });
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
        this.segmenter.events.addEventListener('baseline-editor:new-line', function(event) {
            let line = event.detail;
            this.remoteSave('lines', line);
            this.pushHistory(
                function() {  // undo
                    line.remove();
                    this.remoteDelete('lines', line);
                }.bind(this),
                function() {  // redo
                    let ratio = this.$img.get(0).naturalWidth / this.part.image.size[0];
                    line = this.segmenter.createLine(line.baseline, line.mask);
                    this.remoteSave('lines', line);
                }.bind(this));
        }.bind(this));
        
        this.segmenter.events.addEventListener('baseline-editor:delete-line', function(event) {
            let line = event.detail;
            this.remoteDelete('lines', line);
            this.pushHistory(
                function() {  // undo
                    let ratio = this.$img.get(0).naturalWidth / this.part.image.size[0];
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
            let previous = event.detail.previous;
            this.remoteSave('lines', line);
            console.log(this);
            this.pushHistory(
                function() {  //undo
                    line.update(previous.baseline, previous.mask);
                    this.remoteSave('lines', line);
                    previous = line;
                }.bind(this),
                function() {  // redo
                    line.update(previous.baseline, previous.mask);
                    this.remoteSave('lines', line);
                    previous = line;
                }.bind(this));
        }.bind(this));
        
        // avoid triggering keybindings events when not using the baseline segmenter
        this.segmenter.disableBindings = true;
        this.$panel.on('mouseover', function(e) {
            this.segmenter.disableBindings = false;
        }.bind(this));
        this.$panel.on('mouseout', function(e) {
            this.segmenter.disableBindings = true;
        }.bind(this));
    }
    
    init() {
        function init_() {
            this.segmenter.init();
            let ratio = this.$img.get(0).naturalWidth / this.part.image.size[0];
            // change the coordinate system to fit the thumbnail
            let lines = this.part.lines.map(l => { return {
                pk: l.pk,
                baseline: l.baseline.map(pt => [pt[0]*ratio, pt[1]*ratio]),
                mask: l.mask.map(pt => [pt[0]*ratio, pt[1]*ratio])
            }});
            let regions = this.part.blocks.map(b => { return {
                pk: b.pk,
                box: b.box.map(pt => [pt[0]*ratio, pt[1]*ratio])
            }});
            this.segmenter.load({
                lines: lines, regions: regions
            });
            this.bindZoom();
        }

        if (this.$img.get(0).complete) init_.bind(this)();
        else this.$img.on('load', init_.bind(this));
    }
    
    load(part) {
        super.load(part);
        if (this.part.image.thumbnails) {
            this.$img.attr('src', this.part.image.thumbnails.large);
        } else {
            this.$img.attr('src', this.part.image.uri);
        }
    }

    onShow() {
        this.init();
    }

    convertPolygon(poly, ratio) {
        return poly.map(pt => [Math.round(pt[0]*ratio),
                               Math.round(pt[1]*ratio)]);
    }
    
    remoteSave(type, obj) {
        var post = {document_part: this.part.pk};
        let ratio = this.part.image.size[0] / this.$img.get(0).naturalWidth;
        if (type=='lines') {
            // back to original's image coordinate system (instead of thumbnail's)
            let line = this.convertPolygon(obj.baseline, ratio);
            post['baseline'] = JSON.stringify(line);
            let mask = obj.mask ? this.convertPolygon(obj.mask, ratio) : null;
            post['mask'] = JSON.stringify(mask);
            // post.block = this.block?this.block.pk:null; // todo
        } else if (type == 'blocks') {
            let polygon = this.convertPolygon(obj.polygon);
            post['box'] = JSON.stringify(polygon);
        }
        let uri = this.api + type + '/';
        let pk = obj.context.pk;
        if (pk) uri += pk+'/';
        var requestType = pk?'PUT':'POST';
        $.ajax({url: uri, type: requestType, data: post})
            .done($.proxy(function(data) {
                obj.context.pk = data.pk;
                
                if (type == 'lines') {
                    obj.update(this.convertPolygon(data.baseline, 1/ratio),
                               this.convertPolygon(data.mask, 1/ratio));
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
                    obj.update(this.convertPolygon(data.polygon, 1/ratio));
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
            var tl = panels['trans'].lines.find(l => l.pk==obj.context.pk);
            if (tl) tl.delete();
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
        zoom.refresh();
        var img = this.$img.get(0);
        zoom.events.addEventListener('wheelzoom.updated', function(e) {
            if (!this.opened) return;
            this.segmenter.scale = zoom.scale;
            this.segmenter.canvas.style.top = zoom.pos.y + 'px';
            this.segmenter.canvas.style.left = zoom.pos.x + 'px';
            this.segmenter.canvas.style.width = img.width*zoom.scale + 'px';
            this.segmenter.canvas.style.height = img.height*zoom.scale + 'px';
            this.segmenter.refresh();
        }.bind(this));
    }
}
