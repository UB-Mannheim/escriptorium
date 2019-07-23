/*
Baseline editor
a javascript based baseline segmentation editor,
requires paper.js and colorThief is optional.

Usage:
var segmenter = new Segmenter(img, options);
segmenter.load([{baseline: [[0,0],[10,10]], mask: null}]);

Options:
  lengthTreshold=15
  disableMasks=false // td
  mainColor
  secondaryColor
  lengthTreshold=15,
  delayInit=false,
  deletePointBtn=null,
  deleteLineBtn=null,
  toggleLineBtn=null,
  splitBtn=null,
  mergeBtn=null,
  upperLineHeight=15,
  lowerLineHeight=5

  stateUpdateCallback=null,  // history (undo/redo)
  newLineCallback
  updateLineCallback
  deleteLineCallback
  stateUpdateCallback(stateIndex, stateLength)

*/

function isRightClick(event) {
    return event.which === 3 || event.button === 2;
}

class SegmenterRegion {
    constructor(polygon, segmenter_) {
        this.segmenter = segmenter_;
        this.polygon = polygon;
        this.selected = false;
        this.changed = false;
        this.polygonPath = new Path({
            closed: true,
            opacity: 0.2,
            strokeColor: this.segmenter.mainColor,
            strokeWidth: 1,
            fillColor: this.segmenter.mode == 'regions' ? this.segmenter.secondaryColor : null,
            // selectedColor: this.segmenter.secondaryColor,
            visible: true,
            segments: this.polygon
        });
    }

    select() {
        if (this.selected) return;
        this.polygonPath.selected = true;
        this.polygonPath.bringToFront();
        this.segmenter.addToSelection(this);
        this.selected = true;
    }

    unselect() {
        if (!this.selected) return;
        this.polygonPath.selected = false;
        this.segmenter.removeFromSelection(this);
        this.selected = false;
    }

    toggleSelect() {
        if (this.selected) this.unselect();
        else this.select();
    }
    
    updateDataFromCanvas() {
        this.polygon = this.polygonPath.segments.map(s => [Math.round(s.point.x), Math.round(s.point.y)]);
    }
    
    remove() {
        this.polygonPath.remove();
    }

    delete() {
        this.remove();
        // td: callback
    }
}

class SegmenterLine {
    constructor(baseline, mask, segmenter_) {
        this.segmenter = segmenter_;

        this.mask = mask;
        this.selected = false;
        this.changed = false;

        this.directionHint = null;
        
        var line_ = this;  // save in scope

        this.maskPath = new Path({
            closed: true,
            opacity: 0.1,
            fillColor: this.segmenter.mainColor,
            selectedColor: this.segmenter.secondaryColor,
            visible: this.segmenter.showMasks,
            segments: this.mask
        });

        if (baseline.segments) {  // already a paperjs.Path
            this.baselinePath = baseline;
            this.updateDataFromCanvas();
        } else {
            this.baseline = baseline;
            this.baselinePath = new Path({
                strokeColor: segmenter_.mainColor,
                strokeWidth: 7,
                strokeCap: 'round',
                selectedColor: 'black',
                opacity: 0.5,
                segments: this.baseline,
                selected: false,
                visible: true
            });

            this.showDirection();
        }
    }

    createPolygonEdgeForBaselineSegment(segment) {
        let pt = segment.point;
        let vector = segment.path.getNormalAt(segment.index);
        if (Math.sin(vector.angle/180*Math.PI) > 0) vector = vector.rotate(180);  // right to left
        
        vector.length = this.segmenter.upperLineHeight;
        let up = this.maskPath.insert(segment.index, pt.add(vector));
        
        vector.length = this.segmenter.lowerLineHeight;
        let low = this.maskPath.insert(this.maskPath.segments.length-segment.index, pt.subtract(vector));
        return [up, low];
    }
    deletePolygonsEdgeForBaselineSegment(segment) {
        this.maskPath.removeSegment(this.maskPath.segments.length-segment.index-1);
        this.maskPath.removeSegment(segment.index);
    }
    
    createMask() {
        for (let i in this.baselinePath.segments) {
            this.createPolygonEdgeForBaselineSegment(this.baselinePath.segments[i]);
        }
        this.updateDataFromCanvas();
        this.setLineHeight();
    }
    
    dragPolyEdges(j, delta) {
        let poly = this.maskPath;
        if (poly && poly.segments.length) {
            let top = poly.segments[this.baselinePath.segments.length*2 - j - 1].point;
            let bottom = poly.segments[j].point;
            this.segmenter.movePointInView(top, delta);
            this.segmenter.movePointInView(bottom, delta);
        }
    }
    
    select() {
        if (this.selected) return;
        if (this.maskPath && this.maskPath.visible) this.maskPath.selected = true;
        this.baselinePath.selected = true;
        this.baselinePath.bringToFront();
        this.baselinePath.strokeColor = this.segmenter.secondaryColor;
        if (this.directionHint) this.directionHint.visible = true;
        else this.showDirection();
        this.segmenter.addToSelection(this);
        this.selected = true;
    }

    unselect() {
        if (!this.selected) return;
        if (this.maskPath) this.maskPath.selected = false;
        this.baselinePath.selected = false;
        this.baselinePath.strokeColor = this.segmenter.mainColor;
        this.segmenter.removeFromSelection(this);
        this.directionHint.visible = false;
        this.selected = false;
    }
    
    toggleSelect() {
        if (this.selected) this.unselect();
        else this.select();
    }

    updateDataFromCanvas() {
        this.baseline = this.baselinePath.segments.map(s => [Math.round(s.point.x), Math.round(s.point.y)]);
        this.mask = this.maskPath.segments.map(s => [Math.round(s.point.x), Math.round(s.point.y)]);
    }
    
    extend(point) {
        return this.baselinePath.add(point);
    }
    
    close() {
        if (this.baselinePath.length < this.segmenter.lengthThreshold) {
            this.delete();
        }
        this.baselinePath.smooth({ type: 'catmull-rom', 'factor': 0.2 });
        this.createMask();
    }
    
    remove() {
        this.unselect();
        this.baselinePath.remove();
        this.maskPath.remove();
        this.segmenter.lines.splice(this.segmenter.lines.indexOf(this), 1);
    }

    delete() {
        this.remove();
        /* Callback for line deletion */
    }
    
    showDirection() {
        if (this.baselinePath.segments.length > 1) {
            if (this.directionHint) this.directionHint.remove();
            let vector = this.baselinePath.segments[1].point.subtract(this.baselinePath.firstSegment.point);
            vector.length = 20;
            var start = this.baselinePath.firstSegment.point;
            var end = start.add(vector);
            vector.length = 10;
            this.directionHint =  new Path({
                visible: this.selected,
                shadowColor: 'white', shadowOffset: new Point(1,1), shadowBlur: 1,
                strokeWidth: 1, strokeColor: this.segmenter.mainColor, opacity: 1,
                segments:[
                    end.add(vector.rotate(-150)),
                    end,
                    end.add(vector.rotate(150))]
            });
            if (Math.cos(vector.angle/180*Math.PI) > 0) this.directionHint.translate(vector.rotate(90));
            else this.directionHint.translate(vector.rotate(-90));
        }
    }
    
    setLineHeight() {
        if (this.mask) {
            // distance avg implementation
            /* let sum = 0;
            this.baseline.forEach(function(segment){
                let top = this.maskPath.segments[this.maskPath.segments.length-segment.index-1];
                let bottom = this.maskPath.segments[segment.index];
                sum += top.distance(bottom);
            }.bind(this));
            return sum / this.baseline.length; */

            // area implementation
            this.lineHeight = Math.abs(this.maskPath.area) / this.baselinePath.length;
            if (this.lineHeight) {
                this.baselinePath.strokeWidth = Math.max(this.lineHeight / 6, 3);
            }
        }
    }
}

class Segmenter {
    constructor(image, {lengthTreshold=10,
                        delayInit=false,
                        stateUpdateCallback=null,
                        deletePointBtn=null,
                        deleteLineBtn=null,
                        toggleLineBtn=null,
                        toggleRegionModeBtn=null,
                        splitBtn=null,
                        mergeBtn=null,
                        disableMasks=false, // td
                        mainColor=null,
                        secondaryColor=null,
                        upperLineHeight=20,
                        lowerLineHeight=10
                       }) {
        this.img = image;
        this.canvas = document.createElement('canvas');
        this.canvas.className += 'resize';
        // this.raster = null;
        // insert after..
        this.img.parentNode.insertBefore(this.canvas, this.img);
        this.imgRatio = 1;
        this.mainColor = null;
        this.secondaryColor = null;
        this.upperLineHeight = upperLineHeight;
        this.lowerLineHeight = lowerLineHeight;
        
        this.lines = [];
        this.regions = [];
        this.selection = [];
        // the minimal length in pixels below which the line will be removed automatically
        this.lengthThreshold = lengthTreshold;
        this.showMasks = false;

        this.mode = 'lines'; // | 'regions'
        this.selecting = null;
        this.spliting = false;
        this.copy = null;
        
        this.stateIndex = -1;
        this.states = [];
        this.maxStates = 30;
        
        this.deletePointBtn = deletePointBtn || document.getElementById('delete-point');
        this.deletePointBtn.style.zIndex = 3;
        this.deleteLineBtn = deleteLineBtn || document.getElementById('delete-line');
        this.deleteLineBtn.style.zIndex = 3;
        this.toggleMasksBtn = toggleLineBtn || document.getElementById('toggle-masks');
        this.splitBtn = splitBtn || document.getElementById('split-lines');
        this.mergeBtn = mergeBtn || document.getElementById('merge-lines');
        this.toggleRegionModeBtn = toggleRegionModeBtn || document.getElementById('toggle-regions');
        
        // callbacks
        this.stateUpdateCallback = stateUpdateCallback;
        
        // init paperjs
        if (!delayInit) {
            this.init();
        }
    }

    init(event) {
        paper.settings.handleSize = 10;
        paper.settings.hitTolerance = 10;  // Note: doesn't work?
        paper.install(window);
        paper.setup(this.canvas);

        var hitOptions = { type : ('path'), segments: true, stroke: true, fill: true, tolerance: 5 };
        
        var tool = new Tool();
        this.setColors(this.img);
        this.setCursor();

        // disable right click menu
        this.canvas.addEventListener('contextmenu', function(e) { e.preventDefault(); });
        // make sure we capture clicks before the img
        this.canvas.style.zIndex = this.canvas.style.zIndex + 1;
        
        this.imgRatio = this.img.width / this.img.naturalWidth;
        this.canvas.style.width = this.img.width;
        this.canvas.style.height = this.img.height;
        // this.raster = new Raster(this.img);  // Note: this seems to slow down everything significantly
        // this.raster.position = view.center;
        this.img.style.display = 'hidden';
        
        this.addState();
        
        tool.onMouseDown = this.onMouseDown.bind(this);
        
        this.deleteLineBtn.addEventListener('click', function(event) {
            for (let i=this.selection.length-1; i >= 0; i--) {    
                this.selection[i].delete();
            }
            this.addState();
        }.bind(this));

        this.toggleRegionModeBtn.addEventListener('click', function(event) {
            this.toggleRegionMode();
        }.bind(this));
        
        this.toggleMasksBtn.addEventListener('click', function(event) {
            this.toggleMasks();
        }.bind(this));

        this.splitBtn.addEventListener('click', function(event) {
            this.spliting = !this.spliting;
            this.splitBtn.classList.toggle('btn-info');
            this.splitBtn.classList.toggle('btn-success');
            this.setCursor();
        }.bind(this));

        this.mergeBtn.addEventListener('click', function(event) {
            this.mergeSelection();
            this.addState();
        }.bind(this));
        
        document.addEventListener('keyup', function(event) {
            if (event.keyCode == 27) { // escape
                this.purgeSelection();
            } else if (event.keyCode == 46) { // supr
                for (let i=this.selection.length-1; i >= 0; i--) {    
                    this.selection[i].delete();
                }
            } else if (event.keyCode == 67) { // C
                this.spliting = !this.spliting;
                this.splitBtn.classList.toggle('btn-info');
                this.splitBtn.classList.toggle('btn-success');
                this.setCursor();
            } else if (event.keyCode == 77) { // M
                this.toggleMasks();
            } else if (event.keyCode == 82) { // R
                this.toggleRegionMode();
            }
            // } else if (event.keyCode == 67 && event.ctrlKey) {  // Ctrl+C
            //     this.copy = this.selection.map(a => [
            //         a.baselinePath.exportJSON({asString: false})[1].segments,
            //         a.maskPath.exportJSON({asString: false})[1].segments
            //     ]);
            // } else if (event.keyCode == 86 && event.ctrlKey) {  // Ctrl+V
            //     if (this.copy && this.copy.length) {
            //         var vector, lastPt, beforeLastPt;
            //         if (this.lines.length >= 2) {
            //             lastPt = this.lines[this.lines.length-1].baselinePath.segments[0].point;
            //             beforeLastPt = this.lines[this.lines.length-2].baselinePath.segments[0].point;
            //             vector = new Point(lastPt - beforeLastPt);
            //         } else {
            //             vector = { x: 0, y: 30 };
            //         }
                        
            //         for (let i in this.copy) {
            //             let newLine = this.createLine(this.copy[i][0], this.copy[i][1]);
            //             newLine.changed = true;
            //             if (lastPt) {
            //                 let newLastPt = this.lines[this.lines.length-1].baselinePath.segments[0].point;
            //                 vector = new Point(
            //                     (newLastPt.x - newLine.baseline[0][0]) + vector.x,
            //                     (newLastPt.y - newLine.baseline[0][1]) + vector.y
            //                 );
            //             }
            //             newLine.baselinePath.translate(vector);
            //             newLine.maskPath.translate(vector);
            //         }
            //     }
            
        }.bind(this));

        document.addEventListener('click', function(event) {
            if (event.target != this.canvas) {
                this.purgeSelection();
            }
        }.bind(this));

        this.tool = tool;
        return tool;
    }
    
    createLine(baseline, mask, postponeEvents) {
        var line = new SegmenterLine(baseline, mask, this);
        if (!postponeEvents) this.bindLineEvents(line);
        this.lines.push(line);
        return line;
    }

    finishLine(line) {
        line.close();
        this.bindLineEvents(line);
        this.resetToolEvents();  // unregistering
        this.addState();
    }

    createRegion(polygon, postponeEvents) {
        var region = new SegmenterRegion(polygon, this);
        if (!postponeEvents) this.bindRegionEvents(region);
        this.regions.push(region);
        return region;
    }

    finishRegion(region) {
        this.bindRegionEvents(region);
        this.resetToolEvents();
        region.updateDataFromCanvas();
        this.addState();
    }

    bindRegionEvents(region) {
        region.polygonPath.onMouseDown = function(event) {
            if (event.event.ctrlKey || this.mode != 'regions') return;
            this.selecting = region;
            
            var dragging = region.polygonPath.getNearestLocation(event.point).segment;
            this.tool.onMouseDrag = function(event) {
                if (event.event.ctrlKey) {
                    this.multiMove(event);
                } else {
                    this.movePointInView(dragging.point, event.delta);
                    region.changed = true;
                }
                
            }.bind(this);

            var hit = region.polygonPath.hitTest(event.point, {
	            segments: true,
	            tolerance: 20
            });
            if (hit && hit.type=='segment' && region.polygon.length > 3) {
                let pt = view.projectToView(hit.segment.point);
                this.deletePointBtn.style.left = pt.x - 20 + 'px';
                this.deletePointBtn.style.top = pt.y - 40 + 'px';
                this.deletePointBtn.style.display = 'inline';
                this.deletePointBtn.addEventListener('click', function() {
                    hit.segment.remove();
                    this.deletePointBtn.style.display = 'none';
                    region.updateDataFromCanvas();
                    this.addState();
                }.bind(this), {once: true});
            }
            this.tool.onMouseUp = function(event) {
                this.resetToolEvents();
                let changes = this.updateRegionsFromCanvas();
                if (changes) this.addState();
            }.bind(this);
        }.bind(this);

        region.polygonPath.onDoubleClick = function(event) {
            if (event.event.ctrlKey || this.mode != 'regions') return;
            let location = region.polygonPath.getNearestLocation(event.point);
            let newSegment = region.polygonPath.insert(location.index+1, location);
            region.changed = true;
            this.addState();
        }.bind(this);
    }
    
    bindLineEvents(line) {
        line.baselinePath.onMouseDown = function(event) {
            if (event.event.ctrlKey || this.mode != 'lines' || this.selecting) return;
            this.selecting = line;
            var hit = line.baselinePath.hitTest(event.point, {
	            segments: true,
	            tolerance: 20
            });
            
            if (hit && hit.type=='segment' &&
                hit.segment.index != 0 &&
                hit.segment.index != hit.segment.path.segments.length-1) {
                let pt = view.projectToView(hit.segment.point);
                this.deletePointBtn.style.left = pt.x - 20 + 'px';
                this.deletePointBtn.style.top = pt.y - 40 + 'px';
                this.deletePointBtn.style.display = 'inline';
                this.deletePointBtn.addEventListener('click', function() {
                    line.deletePolygonsEdgeForBaselineSegment(hit.segment);
                    hit.segment.remove();
                    this.deletePointBtn.style.display = 'none';
                    this.addState();
                }.bind(this), {once: true});
            }
            
            var dragging = line.baselinePath.getNearestLocation(event.point).segment;
            this.tool.onMouseDrag = function(event) {
                if (event.event.ctrlKey) {
                    this.multiMove(event);
                } else {
                    this.movePointInView(dragging.point, event.delta);
                    line.showDirection();
                    line.dragPolyEdges(dragging.index, event.delta);
                    line.changed = true;
                }
            }.bind(this);
            
            this.tool.onMouseUp = function(event) {
                this.resetToolEvents();
                let changes = this.updateLinesFromCanvas();
                if (changes) this.addState();
            }.bind(this);
            
        }.bind(this);
        
        line.baselinePath.onDoubleClick = function(event) {
            if (event.event.ctrlKey || this.mode != 'lines') return;
            let location = line.baselinePath.getNearestLocation(event.point);
            let newSegment = line.baselinePath.insert(location.index+1, location);
            line.baselinePath.smooth({ type: 'catmull-rom', 'factor': 0.2 });
            line.createPolygonEdgeForBaselineSegment(newSegment);
            line.changed = true;
        }.bind(this);
        
        line.baselinePath.onMouseMove = function(event) {
            if (event.event.ctrlKey || this.mode != 'lines') return;
            if (line.selected) this.setCursor('grab');
            else this.setCursor('pointer');
            var hit = line.baselinePath.hitTest(event.point, {
	            segments: true,
	            tolerance: 5
            });
            if (hit && hit.type=='segment' &&
                hit.segment.index != 0 &&
                hit.segment.index != hit.segment.path.segments.length-1) {
                this.setCursor('pointer');
            }
        }.bind(this);
        
        line.baselinePath.onMouseLeave = function(event) {
            this.setCursor();
        }.bind(this);
        
        line.baselinePath.onMouseDrag = function(event) {
            if (event.event.ctrlKey || this.mode != 'lines') return;
            this.setCursor('move');
        }.bind(this);

        // same for the masks
        line.maskPath.onMouseDown = function(event) {
            if (event.event.ctrlKey || this.mode != 'lines') return;
            this.selecting = line;

            var dragging = line.maskPath.getNearestLocation(event.point).segment;
            this.tool.onMouseDrag = function(event) {
                if (event.event.ctrlKey) {
                    this.multiMove(event);
                } else {
                    this.movePointInView(dragging.point, event.delta);
                    line.changed = true;
                }
            }.bind(this);
            
            this.tool.onMouseUp = function(event) {
                this.resetToolEvents();
                let changes = this.updateLinesFromCanvas();
                if (changes) {
                    this.addState();
                    line.setLineHeight();
                }
            }.bind(this);
        }.bind(this);
        line.maskPath.onMouseMove = function(event) {
            if (event.event.ctrlKey || this.mode != 'lines') return;
            if (line.selected) this.setCursor('grab');
            else this.setCursor('pointer');
        }.bind(this);
        line.maskPath.onMouseLeave = function(event) {
           this.setCursor();
        }.bind(this);
        line.maskPath.onMouseDrag = function(event) {
            if (event.event.ctrlKey || this.mode != 'lines') return;
           this.setCursor('move');
        }.bind(this);
        
    }
    
    resetToolEvents() {
        this.tool.onMouseDown = this.onMouseDown.bind(this);
        this.tool.onMouseDrag = this.onMouseDrag.bind(this);
        this.tool.onMouseMove = null;
        this.tool.onMouseUp = null;
    }

    multiMove(event) {
        // multi move
        if (this.mode == 'lines') {
            for (let i in this.selection) {
                this.movePointInView(this.selection[i].baselinePath.position, event.delta);
                this.movePointInView(this.selection[i].maskPath.position, event.delta);
                this.selection[i].showDirection();
                this.selection[i].changed = true;
            }
        } else if (this.mode == 'regions') {
            for (let i in this.selection) {
                this.movePointInView(this.selection[i].polygonPath.position, event.delta);
                // this.selection[i].polygonPath.position = this.selection[i].polygonPath.position.add(event.delta);
                this.selection[i].changed = true;
            }
        }
    }
    
    onMouseDrag (event) {
        if (event.event.ctrlKey) this.multiMove(event);
    }
    
    onMouseDown (event) {
        if (isRightClick(event.event)) return;
        
        if (this.selecting) {
            // selection
            if (event.event.shiftKey) {
                this.selecting.toggleSelect();
            } else {
                this.selecting.select();
                this.purgeSelection(this.selecting);
            }
            this.selecting = null;
        } else {
            if (event.event.ctrlKey) return;
            if (this.spliting) {
                this.startCuter(event);
            } else if (event.event.shiftKey) {
                // lasso selection tool
                this.startLassoSelection(event);
            } else if (this.mode == 'regions') {
                this.startNewRegion(event);
            } else {  // mode = 'lines'
                // create a new line
                this.startNewLine(event);
            }
        }
    }

    startNewLine(event) {
        this.purgeSelection();
        let newLine = this.createLine([[event.point.x, event.point.y]], null, true);
        let point = newLine.extend(event.point).point;  // the point that we move around
        newLine.showDirection();
        
        // adds all the events bindings 
        let onCancel = function(event) {
            if (event.keyCode == 27) {  // escape
                newLine.remove();
                this.resetToolEvents();
                document.removeEventListener('keyup', onCancel);
                return false;
            }
            return null;
        }.bind(this);
        
        this.tool.onMouseDown = function(event) {
            if (isRightClick(event.event)) {
                point = newLine.extend(event.point).point;
            } else {
                this.finishLine(newLine);
                document.removeEventListener('keyup', onCancel);
            }
        }.bind(this);
        this.tool.onMouseMove = function(event) {
            this.tool.onMouseDrag = null; // manually disable free drawing now to avoid having both
            // follow the mouse cursor with the last created point
            this.movePointInView(point, event.delta);
            newLine.showDirection();
            newLine.select();  // select it to make drawing more precise
        }.bind(this);
        this.tool.onMouseDrag = function(event) {
            // adding points to current line
            this.tool.onMouseMove = null; // we don't want the first point to move around
            point = newLine.extend(event.point).point;
            this.tool.onMouseUp = function(event) {
                newLine.baselinePath.simplify(10);
                this.finishLine(newLine);
                document.removeEventListener('keyup', onCancel);
            }.bind(this);
        }.bind(this);
        document.addEventListener('keyup', onCancel);
    }

    startNewRegion(event) {
        this.purgeSelection();
        var originPoint = event.point;
        let newRegion = this.createRegion([
            [event.point.x, event.point.y],
            [event.point.x, event.point.y+1],
            [event.point.x+1, event.point.y+1],
            [event.point.x+1, event.point.y]
        ]);
        newRegion.changed = true;
        
        let onCancel = function(event) {
            if (event.keyCode == 27) {  // escape
                newRegion.remove();
                this.resetToolEvents();
                document.removeEventListener('keyup', onCancel);
                return false;
            }
            return null;
        }.bind(this);
        let onRegionDraw = function(event) {
            newRegion.polygonPath.segments[1].point.y = event.point.y;
            newRegion.polygonPath.segments[2].point.x = event.point.x;
            newRegion.polygonPath.segments[2].point.y = event.point.y;
            newRegion.polygonPath.segments[3].point.x = event.point.x;
        }.bind(this);
        
        this.tool.onMouseDown = function(event) {
            this.finishRegion(newRegion);
            document.removeEventListener('keyup', onCancel);
        }.bind(this);
        this.tool.onMouseMove = onRegionDraw;
        this.tool.onMouseDrag = function(event) {
            this.tool.onMouseUp = function(event) {
                this.finishRegion(newRegion);
                document.removeEventListener('keyup', onCancel);
            }.bind(this);
            onRegionDraw(event);
        }.bind(this);
        document.addEventListener('keyup', onCancel);
    }
        
    startCuter(event) {
        // rectangle cutter
        let clip = this.makeSelectionRectangle(event);
        let onCancel = function(event) {
            if (event.keyCode == 27) {  // escape
                clip.remove();
                this.resetToolEvents();
                document.removeEventListener('keyup', onCancel);
                return false;
            }
            return null;
        }.bind(this);

        this.tool.onMouseDrag = function(event) {
            this.updateSelectionRectangle(clip, event);
            this.splitHelper(clip, event);
        }.bind(this);
        this.tool.onMouseUp = function(event) {
            this.splitByPath(clip);
            clip.remove();
            this.resetToolEvents();
            document.removeEventListener('keyup', onCancel);
        }.bind(this);
        document.addEventListener('keyup', onCancel);
    }

    startLassoSelection(event) {
        let clip = this.makeSelectionRectangle(event);
        let onCancel = function(event) {
            if (event.keyCode == 27) {  // escape
                clip.remove();
                this.purgeSelection();
                this.resetToolEvents();
                document.removeEventListener('keyup', onCancel);
                return false;
            }
            return null;
        }.bind(this);
        this.tool.onMouseDrag = function(event) {
            this.updateSelectionRectangle(clip, event);
            this.lassoSelection(clip);
        }.bind(this);
        this.tool.onMouseUp = function(event) {
            clip.remove();
            this.resetToolEvents();
            document.removeEventListener('keyup', onCancel);
        }.bind(this);
        document.addEventListener('keyup', onCancel);
    }
    
    movePointInView(point, delta) {
        point.x += delta.x;
        point.y += delta.y;
        if (point.x < 0) point.x = 0;
        if (point.x > this.img.width) point.x = this.img.width;
        if (point.y < 0) point.y = 0;
        if (point.y > this.img.height) point.y = this.img.height;
    }

    reset() {
        // TODO: reset imgRatio and internals stuff too
        for (let i=this.lines.length-1; i >= 0; i--) {
            this.lines[i].remove();
        };
        for (let i=this.regions.length-1; i >= 0; i--) {
            this.regions[i].remove();
        };
        this.lines = [];
        this.regions = [];
    }
    
    load(data) {
        /* Loads a list of lines containing each a baseline polygon and a mask polygon
         * [{baseline: [[x1, y1], [x2, y2], ..], mask:[[x1, y1], [x2, y2], ]}, {..}] */
        if (data.lines) {
            data.lines.forEach(function(line) {
                let newLine = this.createLine(
                    line.baseline.map(poly => poly.map(coord => Math.round(coord * this.imgRatio))),
                    line.mask.map(poly => poly.map(coord => Math.round(coord * this.imgRatio))));
                if (!newLine.mask) newLine.createMask();
            }.bind(this));
        }
        if (data.regions) {   
            data.regions.forEach(function(region) {
                let newRegion = this.createRegion(
                    region.map(poly => poly.map(coord => Math.round(coord * this.imgRatio)))
                );
            }.bind(this));
        }
    }
    
    exportJSON() {
        /* Returns a list of lines containing each a baseline polygon and a mask polygon
         * {
              regions: [[[xr1, yr1], [xr2, yr2], [xr3, yr3]], [..]],
              lines:[{baseline: [[x1, y1], [x2, y2], ..], mask:[[x1, y1], [x2, y2], ]}, {..}] 
           }
        */
        return {
            regions: this.regions.map(function(region) {
                return region.polygon.map(poly => poly.map(coord => Math.round(coord / this.imgRatio)));
            }.bind(this)),
            lines: this.lines.map(function(line) {
                return {
                    baseline: line.baseline.map(poly => poly.map(coord => Math.round(coord / this.imgRatio))),
                    mask: line.mask.map(poly => poly.map(coord => Math.round(coord / this.imgRatio)))
                };
            }.bind(this))
        };
    }

    loadNextState() {
        if (this.stateIndex >= this.states.length -1) return;
        this.stateIndex++;
        this.loadState(this.stateIndex);        
    }
    
    loadPreviousState() {
        if (this.stateIndex == 0) return;
        this.stateIndex--;
        this.loadState(this.stateIndex);
    }
    
    loadState(index) {
        if (index === undefined) return;
        this.reset();
        this.load(this.states[this.stateIndex]);
        if (this.stateUpdateCallback) this.stateUpdateCallback(this.stateIndex, this.states.length);
    }
    
    addState() {
        if (this.stateIndex < this.maxStates) this.stateIndex++;
        else this.states = this.states.slice(1);
        this.states = this.states.slice(0, this.stateIndex); // cut the state branch
        this.states[this.stateIndex] = this.exportJSON();
        if (this.stateUpdateCallback) this.stateUpdateCallback(this.stateIndex, this.states.length);
    }
    
    updateLinesFromCanvas() {
        var changes = false;
        for (let i in this.lines) {
            if (this.lines[i].changed) {
                this.lines[i].updateDataFromCanvas();
                console.log('UPDATED LINE ' + i);
                // TODO: trigger event or callback
                this.lines[i].changed = false;
                changes = true;
            }
        }
        return changes;
    }
    
    updateRegionsFromCanvas() {
        var changes = false;
        for (let i in this.regions) {
            if (this.regions[i].changed) {
                this.regions[i].updateDataFromCanvas();
                console.log('UPDATED REGION ' + i);
                // TODO: trigger event or callback
                this.regions[i].changed = false;
                changes = true;
            }
        }
        return changes;
    }
    
    toggleMasks() {
        this.showMasks = !this.showMasks;
        this.toggleMasksBtn.classList.toggle('btn-success');
        this.toggleMasksBtn.classList.toggle('btn-info');
        for (let i in this.lines) {
            let poly = this.lines[i].maskPath;
            poly.visible = !poly.visible;
            // paperjs shows handles for invisible items :(
            // TODO: use layers?
            if (!poly.visible && poly.selected) poly.selected = false;
            if (poly.visible && this.lines[i].selected) poly.selected = true;
        }
    }

    toggleRegionMode() {
        this.purgeSelection();
        this.mode = this.mode == 'lines' ? 'regions' : 'lines';
        this.toggleRegionModeBtn.classList.toggle('btn-info');
        this.toggleRegionModeBtn.classList.toggle('btn-success');
        this.regions.forEach(function(region) {
            if (this.mode == 'lines') {
                region.polygonPath.fillColor = null;
            } else {
                region.polygonPath.fillColor = this.secondaryColor;
            }
        }.bind(this));
    }
    
    showDeleteLineBtn(line) {
        let pt = view.projectToView(line.baselinePath.bounds.topRight);
        this.deleteLineBtn.style.left = pt.x + 20 + "px";
        this.deleteLineBtn.style.top = pt.y -30 + "px";
        this.deleteLineBtn.style.display = 'inline';
    }
    addToSelection(obj) {
        if (this.selection.indexOf(obj) == -1) this.selection.push(obj);
        if (obj.baselinePath) this.showDeleteLineBtn(obj);
        // if (obj.baselinePath) this.showDeleteRegionBtn(line); // todo
    }
    removeFromSelection(obj) {
        this.selection.splice(this.selection.indexOf(obj), 1);
        this.deletePointBtn.style.display = 'none';
        if (this.selection.length == 0) this.deleteLineBtn.style.display = 'none';
    }
    purgeSelection(except) {
        for (let i=this.selection.length-1; i >= 0; i--) {
            if (!except || except != this.selection[i]) {
                this.selection[i].unselect();
            }
        }
    }

    resetViewSize() {
        paper.view.viewSize = [this.img.width, this.img.height];
    }
    
    makeSelectionRectangle(event) {
        let shape = new Rectangle([event.point.x, event.point.y], [1, 1]);
        var clip = new Path.Rectangle(shape, 0);
        clip.opacity = 1;
        clip.strokeWidth = 2;
        clip.strokeColor = 'grey';
        clip.dashArray = [10, 4];
        clip.originalPoint = event.point;
        return clip;
    }

    updateSelectionRectangle(clip, event) {
        clip.bounds.width = Math.max(1, Math.abs(clip.originalPoint.x - event.point.x));
        if (event.point.x > clip.originalPoint.x) {
            clip.bounds.x = clip.originalPoint.x;
        } else {
            clip.bounds.x = event.point.x;
        }
        clip.bounds.height = Math.max(1, Math.abs(clip.originalPoint.y - event.point.y));
        if (event.point.y > clip.originalPoint.y) {
            clip.bounds.y = clip.originalPoint.y;
        } else {
            clip.bounds.y = event.point.y;
        }
    }
    
    lassoSelection(clip) {
        // draws a rectangle lasso selection tool that selects every line it crosses
        for (let i in this.lines) {
            let line = this.lines[i];
            if (line.selected) {continue;}  // avoid calculs
            if (clip.intersects(line.baselinePath) ||
                line.baselinePath.isInside(clip.bounds)) {
                line.select();
            }
        }
    }
    
    splitHelper(clip, event) {
        this.lines.forEach(function(line) {
            let intersections = line.baselinePath.getIntersections(clip);
            for (var i = 0; i < intersections.length; i++) {
                new Path.Circle({
                    center: intersections[i].point,
                    radius: 5,
                    fillColor: 'red'
                }).removeOnDrag().removeOnUp();

                if (intersections.length) {
                    // show what is going to be cut
                    let cut = new Path({strokeColor: 'red', strokeWidth: 2}).removeOnDrag().removeOnUp();
                    intersections.forEach(location => cut.add(location));
                    cut.bringToFront();
                    line.baselinePath.segments.forEach(function(segment) {
                        if (clip.contains(segment.point)) {
                            cut.insert(segment.index, segment);
                        }
                    }.bind(this));
                }
            }
        }.bind(this));
    }
    
    splitByPath(path) {
        this.lines.forEach(function(line) {
            let intersections = line.baselinePath.getIntersections(path);
            for (var i = 0; i < intersections.length; i += 2) {
                if (i+1 >= intersections.length) {  // one intersection remaining
                    // remove everything in the selection rectangle
                    let location = intersections[i];
                    let newSegment = line.baselinePath.insert(location.index+1, location);
                    if (path.contains(line.baselinePath.firstSegment.point)) {
                        line.baselinePath.removeSegments(0, newSegment.index);
                    } else if (path.contains(line.baselinePath.lastSegment.point)) {
                        line.baselinePath.removeSegments(newSegment.index+1);
                    }
                    line.baselinePath.smooth({ type: 'catmull-rom', 'factor': 0.2 });
                    line.createPolygonEdgeForBaselineSegment(newSegment);
                    line.updateDataFromCanvas();
                } else {
                    let newLine = line.baselinePath.splitAt(intersections[i+1]);
                    let nl = this.createLine(newLine);
                    let trash = line.baselinePath.splitAt(intersections[i]);
                    line.maskPath.removeSegments();
                    line.createMask();
                    nl.createMask();
                    line = nl;
                    trash.remove();
                }
            }
            if (i) this.addState();  // if there was any changes, save them
        }.bind(this));
    }
    
    mergeSelection() {
        /* strategy is:
          1) order the lines by their position,
             line direction doesn't matter since .join() can merge from start or end points
          2) join the lines 2 by 2 setting tolerance to the shortest distance between
             the starting and ending points of both lines.
          3) Delete the left over
        */
        
        this.selection.sort(function(first, second) {
            let vertical = false;  // todo
            let vector = first.baselinePath.segments[1].point.subtract(first.baselinePath.firstSegment.point);
            let rightToLeft = Math.cos(vector.angle/180*Math.PI) < 0;  // right to left
            if (vertical) return first.baselinePath.position.y - second.baselinePath.position.y;
            else if (rightToLeft) return second.baselinePath.position.x - first.baselinePath.position.x;
            else return first.baselinePath.position.x - second.baselinePath.position.x;
        });
        
        while (this.selection.length > 1) {
            let seg1 = this.selection[0].baselinePath.getNearestLocation(this.selection[1].baselinePath.interiorPoint);
            let seg2 = this.selection[1].baselinePath.getNearestLocation(this.selection[0].baselinePath.interiorPoint);
            this.selection[0].baselinePath.add(seg2);
            this.selection[0].baselinePath.join(this.selection[1].baselinePath, seg1.point.getDistance(seg2.point));
            
            for (let i in this.selection[1].maskPath.segments) {
                // Note: document advertise it's possible to insert more at once but couldn't make it work
                let insertAt = seg1.segment.index + parseInt(i) + 1;
                this.selection[0].maskPath.insert(insertAt, this.selection[1].maskPath.segments[i]);
            }
            
            this.selection[1].delete();
        }
        if (this.selection) this.selection[0].changed = true;
    }

    setCursor(style) {
        if (style) {
            this.canvas.style.cursor = style;
        } else {
            this.canvas.style.cursor = this.spliting?'crosshair':'copy';
        }
    }
    
    setColors() {
        // Attempt to choose the best color for highlighting
        
        function isGrey_(color) {
            return (
                Math.abs(color[0] - color[1]) < 30 &&
                Math.abs(color[0] - color[2]) < 30 &&
                Math.abs(color[1] - color[2]) < 30
            );
        }
        
        function hasColor_(pal, channel) {
            for (let i in pal) {
                if (isGrey_(pal[i])) {continue;}
                if (pal[i][channel] == Math.max.apply(null, pal[i]) && pal[i][channel] > 100) {
                    // the channel is dominant in this color
                    return true;
                }
            }
            return false;
        }
        
        function chooseColors(pal, depth=0) {
            if (hasColor_(pal, 2)) {
                // has blue
                if (hasColor_(pal, 0)) {
                    // has red
                    if (hasColor_(pal, 1)) {
                        // has green; the document is quite rich, start again with only the 2 main colors
                        pal = pal.slice(0, 2);
                        if (depth < 1) return chooseColors(pal, depth=depth+1);
                        else return ['blue', 'teal']; // give up
                    } else {
                        return ['green', 'yellow'];
                    }
                } else {
                    return ['red', 'orange'];
                }
            } else {
                return ['blue', 'teal'];
            }
        }
        
        const rgbToHex = (c) => '#' + [c[0], c[1], c[2]]
              .map(x => x.toString(16).padStart(2, '0')).join('');

        if (ColorThief !== undefined && !this.mainColor) {
            var colorThief = new ColorThief();
            let palette = colorThief.getPalette(this.img, 5);
            // for (let i in palette) {
            //     let el = document.getElementById('color'+i);
            //     el.style.backgroundColor = rgbToHex(palette[i]);
            //     el.style.padding = '10px';
            // }
            let choices = chooseColors(palette);
            this.mainColor = choices[0];
            this.secondaryColor = choices[1];
        } else {
            this.mainColor = 'blue';
            this.secondaryColor = 'teal';
        }
    }
}
