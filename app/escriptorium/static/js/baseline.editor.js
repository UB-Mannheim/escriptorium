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
  stateUpdateCallback=null,
  deletePointBtn=null,
  deleteLineBtn=null,
  toggleLineBtn=null,
  splitBtn=null,
  mergeBtn=null

  newLineCallback
  updateLineCallback
  deleteLineCallback
  stateUpdateCallback(stateIndex, stateLength)
*/

function isRightClick(event) {
    return event.which === 3 || event.button === 2;
}

class SegmenterRegion {}

class SegmenterLine {
    constructor(baseline, mask, segmenter_) {
        this.segmenter = segmenter_;

        this.mask = mask;
        this.selected = false;
        this.changed = false;
        
        var line_ = this;  // save in scope

        this.maskPath = new Path({
            closed: true,
            opacity: 0.1,
            fillColor: this.segmenter.mainColor,
            selectedColor: this.segmenter.secondaryColor,
            visible: this.segmenter.showMasks,
            segments: this.mask
        });
        this.maskPath.line = this;
        
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
        }
    }

    createPolygonEdgeForBaselineSegment(segment) {
        let pt = segment.point;
        let upperVector = new Point({ angle: pt.angle - 90, length: 20 });
        let up = this.maskPath.insert(segment.index, pt.add(upperVector));

        let lowerVector = new Point({ angle: pt.angle + 90, length: 10 });
        let low = this.maskPath.insert(this.maskPath.segments.length-segment.index, pt.add(lowerVector));
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
        // this.getLineHeight();
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
        this.segmenter.addToSelection(this);
        this.selected = true;
    }

    unselect() {
        if (!this.selected) return;
        if (this.maskPath) this.maskPath.selected = false;
        this.baselinePath.selected = false;
        this.baselinePath.strokeColor = this.segmenter.mainColor;
        this.segmenter.removeFromSelection(this);
        this.segmenter.deletePointBtn.style.display = 'none';
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
        this.changed = true;
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
    
    getLineHeight() {
        if (this.mask) {
            let sum = 0;
            this.baseline.forEach(function(segment){
                let top = this.maskPath.segments[this.maskPath.segments.length-segment.index-1];
                let bottom = this.maskPath.segments[segment.index];
                sum += top.subtract(bottom).length;
            }.bind(this));
            return sum / this.baseline.length;
        }
        return null;
    }
}

class Segmenter {
    constructor(image, {lengthTreshold=15,
                        delayInit=false,
                        stateUpdateCallback=null,
                        deletePointBtn=null,
                        deleteLineBtn=null,
                        toggleLineBtn=null,
                        splitBtn=null,
                        mergeBtn=null,
                        disableMasks=false, // td
                        mainColor=null,
                        secondaryColor=null
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
        
        this.lines = [];
        this.selection = [];
        // the minimal length in pixels below which the line will be removed automatically
        this.lengthThreshold = lengthTreshold;
        this.showMasks = false;

        // needed?
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

        //         let changes = this.updateLinesFromCanvas();
        //         if (changes) this.addState();
        
        this.deleteLineBtn.addEventListener('click', function(event) {
            for (let i=this.selection.length-1; i >= 0; i--) {    
                this.selection[i].delete();
            }
            this.addState();
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
                if (this.spliting) {
                    this.spliting = false;
                    if (this.clip) this.clip.remove();
                    this.splitBtn.classList.add('btn-info');
                    this.splitBtn.classList.remove('btn-success');
                    this.setCursor();
                } else {
                    this.purgeSelection();
                }
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

    bindLineEvents(line) {
        line.baselinePath.onMouseDown = function(event) {
            if (event.event.ctrlKey) return;
            this.selecting = line;
            var hit = line.baselinePath.hitTest(event.point, {
	            segments: true,
	            tolerance: 10
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
                }.bind(this));
            }
            
            var dragging = line.baselinePath.getNearestLocation(event.point).segment;
            this.tool.onMouseDrag = function(event) {
                if (event.event.ctrlKey) {
                    this.multiMove(event);
                } else {
                    this.movePointInView(dragging.point, event.delta);
                    line.dragPolyEdges(dragging.index, event.delta);
                    line.changed = true;
                }
            }.bind(this);
            
            this.tool.onMouseUp = function(event) {
                this.resetToolEvents();
            }.bind(this);
            
        }.bind(this);
        
        line.baselinePath.onDoubleClick = function(event) {
            let location = line.baselinePath.getNearestLocation(event.point);
            let newSegment = line.baselinePath.insert(location.index+1, location);
            this.smooth({ type: 'catmull-rom', 'factor': 0.2 });
            line.createPolygonEdgeForBaselineSegment(newSegment);
            line.changed = true;
        };
        
        line.baselinePath.onMouseMove = function(event) {
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
            this.setCursor('move');
        }.bind(this);

        line.maskPath.onMouseDown = function(event) {
            this.selecting = line;
        }.bind(this);
        line.maskPath.onMouseMove = function(event) {
            if (line.selected) this.setCursor('grab');
            else this.setCursor('pointer');
        }.bind(this);
        line.maskPath.onMouseLeave = function(event) {
           this.setCursor();
        }.bind(this);
        line.maskPath.onMouseDrag = function(event) {
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
        for (let i in this.selection) {
            for(let j in this.selection[i].baselinePath.segments) {
                let point = this.selection[i].baselinePath.segments[j].point;
                this.movePointInView(point, event.delta);
                this.selection[i].dragPolyEdges(j, event.delta);
            }
            this.selection[i].changed = true;
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
        } else {
            if (event.event.ctrlKey) return;
            if (this.spliting) {
                // rectangle cutter
                let clip = this.makeSelectionRectangle(event);
                let onCancel = function(event) {
                    if (event.keyCode == 27) {  // escape
                        clip.remove();
                        this.resetToolEvents();
                        document.removeEventListener('keyup', onCancel);
                    }
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
                
            } else if (event.event.shiftKey) {
                // lasso selection tool
                let clip = this.makeSelectionRectangle(event);
                let onCancel = function(event) {
                    if (event.keyCode == 27) {  // escape
                        clip.remove();
                        this.purgeSelection();
                        this.resetToolEvents();
                        document.removeEventListener('keyup', onCancel);
                    }
                    return false;
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
                
            } else {
                // create a new line
                this.purgeSelection();
                let newLine = this.createLine([event.point], null, true);
                let point = newLine.extend(event.point).point;  // the point that we move around

                // adds all the events bindings 
                let onCancel = function(event) {
                    if (event.keyCode == 27) {  // escape
                        newLine.delete();
                        this.resetToolEvents();
                        document.removeEventListener('keyup', onCancel);
                    }
                    return false;
                }.bind(this);
                let finishLine = function(event) {
                    newLine.close();
                    this.bindLineEvents(newLine);
                    newLine.unselect();
                    this.resetToolEvents();  // unregistering
                    document.removeEventListener('keyup', onCancel);
                }.bind(this);
                
                this.tool.onMouseDown = function(event) {
                    if (isRightClick(event.event)) {
                        point = newLine.extend(event.point).point;
                    } else {
                        finishLine();
                    }
                }.bind(this);
                this.tool.onMouseMove = function(event) {
                    this.tool.onMouseDrag = null; // manually disable free drawing now to avoid having both
                    // follow the mouse cursor with the last created point
                    this.movePointInView(point, event.delta);
                    newLine.select();  // select it to make drawing more precise
                }.bind(this);
                this.tool.onMouseDrag = function(event) {
                    // adding points to current line
                    this.tool.onMouseMove = null; // we don't want the first point to move around
                    point = newLine.extend(event.point).point;
                    this.tool.onMouseUp = function(event) {
                        finishLine();
                        newLine.baselinePath.simplify(10);
                    }.bind(this);
                }.bind(this);
                document.addEventListener('keyup', onCancel);
            }
        }
        // if we had something to select, it's already done
        this.selecting = null;
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
        this.lines = [];
    }
    
    load(data) {
        /* Loads a list of lines containing each a baseline polygon and a mask polygon
         * [{baseline: [[x1, y1], [x2, y2], ..], mask:[[x1, y1], [x2, y2], ]}, {..}] */
        
        data.forEach(function(line) {
            let newLine = this.createLine(
                line.baseline.map(poly => poly.map(coord => Math.round(coord * this.imgRatio))),
                line.mask.map(poly => poly.map(coord => Math.round(coord * this.imgRatio))));
            if (!newLine.mask) newLine.createMask();
        }.bind(this));
    }
    
    exportJSON() {
        /* Returns a list of lines containing each a baseline polygon and a mask polygon
         * [{baseline: [[x1, y1], [x2, y2], ..], mask:[[x1, y1], [x2, y2], ]}, {..}] */
        return this.lines.map(function(line) {
            return {
                baseline: line.baseline.map(poly => poly.map(coord => Math.round(coord / this.imgRatio))),
                mask: line.mask.map(poly => poly.map(coord => Math.round(coord / this.imgRatio)))
            };
        }.bind(this));
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
    
    toggleMasks() {
        this.showMasks = !this.showMasks;
        for (let i in this.lines) {
            let poly = this.lines[i].maskPath;
            poly.visible = !poly.visible;
            // paperjs shows handles for invisible items :(
            // TODO: use layers?
            if (!poly.visible && poly.selected) poly.selected = false;
            if (poly.visible && this.lines[i].selected) poly.selected = true;
        }
    }

    showDeleteLineBtn(line) {
        let pt = view.projectToView(line.baselinePath.bounds.topRight);
        this.deleteLineBtn.style.left = pt.x + 20 + "px";
        this.deleteLineBtn.style.top = pt.y -30 + "px";
        this.deleteLineBtn.style.display = 'inline';
    }
    addToSelection(line) {
        if (this.selection.indexOf(line) == -1) this.selection.push(line);
        if (!this.newLine) this.showDeleteLineBtn(line);
    }
    removeFromSelection(line) {
        this.selection.pop(this.selection.indexOf(line));
        if (this.selection.length == 0) this.deleteLineBtn.style.display = 'none';
    }
    purgeSelection(except) {
        for (let i=this.selection.length-1; i >= 0; i--) {
            if (!except || (except && except != this.selection[i])) {
                this.selection[i].unselect();
            }
        }
        if (except) {
            this.selection = [except];
        } else {
            this.selection = [];
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
                    line.updateDataFromCanvas();
                    line = nl;
                    trash.remove();
                }
            }
            if (i) this.addState();  // if there was any changes, save them
        }.bind(this));
    }
    
    mergeSelection() {
        if(this.selection.length < 2) return;
        for(let i = 1; i < this.selection.length; i++) { //loop starts at 1!!
            this.selection[0].baselinePath.join(this.selection[i].baselinePath, 10);
        }
        for(let i = this.selection.length - 1; i > 1; i--) {
            this.selection[i].delete();
        }
        this.selection[0].maskPath.removeSegments();
        this.selection[0].createMask();
        this.selection[0].changed = true;
    }

    setCursor(style) {
        if (style) {
            this.canvas.style.cursor = style;
        } else {
            this.canvas.style.cursor = this.spliting?'crosshair':'copy';
        }
    }
    
    setColors() {
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
