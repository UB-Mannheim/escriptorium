/*
Baseline editor
a javascript based baseline segmentation editor,
requires paper.js and colorThief is optional.

Usage:
new Segmenter(img);
  lengthTreshold=15
  disableMasks=false
  mainColor
  secondaryColor
  splitBtn
  mergeBtn

  newLineCallback
  updateLineCallback
  deleteLineCallback

  segmenter.load(lines)

*/

class SegmenterRegion {}

class SegmenterLine {
    constructor(baseline, polygon, segmenter_) {
        this.segmenter = segmenter_;

        this.polygon = polygon;
        this.selected = false;
        this.changed = false;
        
        var line_ = this;  // save in scope

        this.polygonPath = new Path({
            closed: true,
            opacity: 0.1,
            fillColor: this.segmenter.mainColor,
            visible: this.segmenter.showPolygons,
            segments: this.polygon,
            onMouseDown: function(event) {
                segmenter_.selecting = line_;
                segmenter_.dragging = this.getNearestLocation(event.point).segment;
            },
            onMouseUp: function(event) {
                if(segmenter_.dragging && segmenter_.dragging.path == this.path) {
                    segmenter_.dragging = null;
                }
            }
        });
        this.polygonPath.line = this;

        if (baseline.segments) {  // already a paperjs.Path
            this.baselinePath = baseline;
            this.updateDataFromCanvas();
        } else {
            this.baseline = baseline;
            this.baselinePath = new Path({
                strokeColor: segmenter_.mainColor,
                strokeWidth: 7,
                opacity: 0.5,
                segments: this.baseline,
                selected: false,
                visible: true
            });
        }

        this.baselinePath.onMouseDown = function(event) {
            segmenter_.selecting = line_;
            segmenter_.dragging = this.getNearestLocation(event.point).segment;
            
            var hit = this.hitTest(event.point, {
	            segments: true,
	            tolerance: 5
            });
            if (hit && hit.type=='segment' &&
                hit.segment.index != 0 &&
                hit.segment.index != hit.segment.path.segments.length-1) {
                line_.segmenter.deleting = hit.segment;
            }
        };
        this.baselinePath.onMouseUp = function(event) {
            if(segmenter_.dragging && segmenter_.dragging.path == this.path) {
                segmenter_.dragging = null;
            }
        };
        this.baselinePath.onDoubleClick = function(event) {
            let location = this.getNearestLocation(event.point);
            let newSegment = this.insert(location.index+1, location);
            this.smooth({ type: 'catmull-rom', 'factor': 0.2 });
            line_.createPolygonEdgeForBaselineSegment(newSegment);
            this.line.changed = true;
        };
        this.baselinePath.line = this;
    }

    createPolygonEdgeForBaselineSegment(segment) {
        let pt = segment.point;
        let upperVector = new Point({ angle: pt.angle - 90, length: 20 });
        let up = this.polygonPath.insert(segment.index, pt.add(upperVector));

        let lowerVector = new Point({ angle: pt.angle + 90, length: 10 });
        let low = this.polygonPath.insert(this.polygonPath.segments.length-segment.index, pt.add(lowerVector));
        return [up, low];
    }
    deletePolygonsEdgeForBaselineSegment(segment) {
        this.polygonPath.removeSegment(this.polygonPath.segments.length-segment.index-1);
        this.polygonPath.removeSegment(segment.index);
    }
    
    createPolygon() {
        for (let i in this.baselinePath.segments) {
            this.createPolygonEdgeForBaselineSegment(this.baselinePath.segments[i]);
        }
        // this.getLineHeight();
    }

    dragPolyEdges(j, delta) {
        let poly = this.polygonPath;
        if (poly && poly.segments.length) {
            let top = poly.segments[this.baselinePath.segments.length*2 - j - 1].point;
            let bottom = poly.segments[j].point;
            this.segmenter.movePointInView(top, delta);
            this.segmenter.movePointInView(bottom, delta);
        }
    }
    
    select() {
        if (this.selected) return;
        if (this.polygonPath && this.polygonPath.visible) this.polygonPath.selected = true;
        this.baselinePath.selected = true;
        this.baselinePath.bringToFront();
        this.baselinePath.strokeColor = this.segmenter.secondaryColor;
        this.segmenter.addToSelection(this);
        this.selected = true;
    }

    unselect() {
        if (!this.selected) return;
        if (this.polygonPath) this.polygonPath.selected = false;
        this.baselinePath.selected = false;
        this.baselinePath.strokeColor = this.segmenter.mainColor;
        if (this.segmenter.deleting && this.segmenter.deleting.path == this.baselinePath) {
            this.segmenter.deletePointBtn.style.display = 'none';
        }
        this.segmenter.removeFromSelection(this);
        this.selected = false;
        
        // if (this.changed) {
        //     // TODO: trigger event or callback
        // }
    }
    
    toggleSelect() {
        if (this.selected) this.unselect();
        else this.select();
    }

    updateDataFromCanvas() {
        this.baseline = this.baselinePath.segments.map(s => [Math.round(s.point.x), Math.round(s.point.y)]);
        this.polygon = this.polygonPath.segments.map(s => [Math.round(s.point.x), Math.round(s.point.y)]);
    }
    
    extend(point) {
        return this.baselinePath.add(point);
    }
    
    close() {
        if (this.baselinePath.length < this.segmenter.lengthThreshold) {
            this.delete();
        }
        this.baselinePath.smooth({ type: 'catmull-rom', 'factor': 0.2 });
        this.createPolygon();
        this.changed = true;
    }
    
    delete() {
        this.unselect();
        this.segmenter.lines.pop(this.segmenter.lines.indexOf(this));
        this.baselinePath.remove();
        this.polygonPath.remove();
        // TODO: trigger event or callback
    }

    getLineHeight() {
        if (this.polygon) {
            let sum = 0;
            this.baseline.forEach(function(segment){
                let top = this.polygonPath.segments[this.polygonPath.segments.length-segment.index-1];
                let bottom = this.polygonPath.segments[segment.index];
                sum += top.subtract(bottom).length;
            }.bind(this));
            return sum / this.baseline.length;
        }
        return null;
    }
}

class Segmenter {
    constructor(image, {lengthTreshold=15, delayInit=false}) {
        this.img = image;
        this.canvas = document.createElement('canvas');
        this.canvas.className += 'resize';
        // insert after..
        this.img.parentNode.insertBefore(this.canvas, this.img.nextElementSibling);
        
        this.lines = [];
        this.selection = [];
        // the minimal length in pixels below which the line will be removed automatically
        this.lengthThreshold = lengthTreshold;
        this.showPolygons = false;

        // needed?
        this.newLine = null;
        this.dragging = null;
        this.drawing = false;
        this.selecting = null;
        this.spliting = false;
        // this.draggingPoint = null;
        this.deleting = null;
        this.clip = null;  // draw a box for multi selection
        this.copy = null;
        this.changed = [];
        
        // TODO: customizable
        this.deletePointBtn = document.getElementById('delete-point');
        this.deleteLineBtn = document.getElementById('delete-line');
        this.togglePolygonsBtn = document.getElementById('toggle-polygons');
        this.splitBtn = document.getElementById('split-lines');
        this.mergeBtn = document.getElementById('merge-lines');
        
        // init paperjs
        if (!delayInit) {
            this.init();
        }
    }

    init(event) {
        paper.install(window);
        paper.settings.handleSize = 10;
        paper.setup(this.canvas);
        var tool = new Tool();
        this.getColors(this.img);
        
        this.canvas.addEventListener('contextmenu', function(e) { e.preventDefault(); });
        
        tool.onMouseDown = function(event) {
            if (event.event.which === 3 || event.event.button === 2) {
                // right click
                if (this.newLine) {
                    // adds a point to the line
                    let pt = this.newLine.extend(event.point);
                    this.dragging = pt;                    
                }
            } else {
                // left click
                if (!event.event.ctrlKey) {
                    if (this.selecting) {
                        if (event.event.shiftKey) {
                            this.selecting.toggleSelect();
                        } else if (this.deleting) {
                            // we clicked on a point in the baseline
                            this.deletePointBtn.style.left = this.deleting.point.x - 20 + 'px';
                            this.deletePointBtn.style.top = this.deleting.point.y - 40 + 'px';
                            this.deletePointBtn.style.display = 'inline';
                        } else {
                            this.selecting.select();
                            this.purgeSelection(this.selecting);
                        }
                    } else if (!this.spliting) {
                        if (!this.newLine) {
                            if (!event.event.shiftKey) {
                                // creates a new line
                                this.purgeSelection();
                                this.newLine = this.createLine([event.point]);
                                let pt = this.newLine.extend(event.point);
                                this.dragging = pt;
                            }
                        } else {
                            // end the line
                            this.newLine.close();
                            this.newLine = null;
                            this.dragging = null;
                            this.selecting = null;
                        }
                        this.purgeSelection();
                        this.deletePointBtn.style.display = 'none';
                        this.deleting = null;
                    }
                }
            }
            
            // if we had something to select, it's already done
            this.selecting = null;
        }.bind(this);
        
        tool.onMouseMove = function(event) {
            if (this.spliting && this.spliter) {
                this.movePointInView(this.spliter.lastSegment.point, event.delta);
            } else if (this.newLine && this.dragging) {
                this.movePointInView(this.dragging.point, event.delta);
            }
        }.bind(this);
        
        tool.onMouseDrag = function(event) {
            if (this.newLine) {
                // adding points to current line
                var pt = this.newLine.extend(event.point);
                this.dragging = pt;
                this.drawing = true;
		    } else if (this.spliting) {
                this.splitTool(event);
            } else if (event.event.ctrlKey) {
                // multi move
                for (let i in this.selection) {
                    for(let j in this.selection[i].baselinePath.segments) {
                        let point = this.selection[i].baselinePath.segments[j].point;
                        this.movePointInView(point, event.delta);
                        this.selection[i].dragPolyEdges(j, event.delta);
                    }
                    this.selection[i].changed = true;
                }
            } else if (event.event.shiftKey) {
                // multi lasso selection
                this.lassoSelection(event);
            } else if (this.dragging) {
                this.movePointInView(this.dragging.point, event.delta);
                if (this.dragging.path.line.baselinePath == this.dragging.path) {
                    this.dragging.path.line.dragPolyEdges(this.dragging.index, event.delta);
                }
                this.dragging.path.line.changed = true;
            } else if (event.event.altKey) {
                // view.rotate(0.1);
            }
        }.bind(this);

        tool.onMouseUp = function(event) {
            if (this.clip) {
                if(this.spliting) {
                    this.splitByPath(this.clip);
                    // this.spliting = false;
                }
                
                this.clip.remove();
                this.clip = null;
            } else {
                this.updateLinesFromCanvas();
            }

            if (!this.newLine) {
                this.dragging = null;
            }

            if (this.drawing) {
                this.newLine.baselinePath.simplify(10);
                this.newLine.close();
                this.newLine = null;
                // this.dragging = null;
                this.selecting = null;
            }

            this.drawing = false;
        }.bind(this);
        
        this.deletePointBtn.addEventListener('click', function(event) {
            if (this.deleting) {
                let line = this.deleting.path.line;
                line.deletePolygonsEdgeForBaselineSegment(this.deleting);
                this.deleting.remove();
                this.deletePointBtn.style.display = 'none';
                this.deleting = null;
            }
            return false;
        }.bind(this));

        this.deleteLineBtn.addEventListener('click', function(event) {
            for (let i=this.selection.length-1; i >= 0; i--) {    
                this.selection[i].delete();
            }
        }.bind(this));
        
        this.togglePolygonsBtn.addEventListener('click', function(event) {
            this.togglePolygons();
        }.bind(this));

        this.splitBtn.addEventListener('click', function(event) {
            this.spliting = !this.spliting;
            this.splitBtn.classList.toggle('btn-success');
        }.bind(this));

        this.mergeBtn.addEventListener('click', function(event) {
            this.mergeSelection();
        }.bind(this));
        
        document.addEventListener('keyup', function(event) {
            if (event.keyCode == 27) { // escape
                if (this.newLine) {
                    this.newLine.delete();
                    this.newLine = null;
                    this.dragging = null;
                } else {
                    this.purgeSelection();
                }
            } else if (event.keyCode == 46) { // supr
                for (let i=this.selection.length-1; i >= 0; i--) {    
                    this.selection[i].delete();
                }
            // } else if (event.keyCode == 67 && event.ctrlKey) {  // Ctrl+C
            //     this.copy = this.selection.map(a => [
            //         a.baselinePath.exportJSON({asString: false})[1].segments,
            //         a.polygonPath.exportJSON({asString: false})[1].segments
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
            //             newLine.polygonPath.translate(vector);
            //         }
            //     }
            }
        }.bind(this));

        document.addEventListener('click', function(event) {
            if (!event.target == this.canvas) {
                this.purgeSelection();
            }
        }.bind(this));
    }
    
    createLine(baseline, mask) {
        var line = new SegmenterLine(baseline, mask, this);
        this.lines.push(line);
        return line;
    }

    movePointInView(point, delta) {
        point.x += delta.x;
        point.y += delta.y;
        if (point.x < 0) point.x = 0;
        if (point.x > view.viewSize.width) point.x = view.viewSize.width;
        if (point.y < 0) point.y = 0;
        if (point.y > view.viewSize.height) point.y = view.viewSize.height;
    }

    updateLinesFromCanvas() {
        for (let i in this.lines) {
            if (this.lines[i].changed) {
                this.lines[i].updateDataFromCanvas();
                console.log('UPDATED LINE ' + i);
                // TODO: trigger event or callback
                this.lines[i].changed = false;
            }
        }
    }
    
    togglePolygons() {
        this.showPolygons = !this.showPolygons;
        for (let i in this.lines) {
            let poly = this.lines[i].polygonPath;
            poly.visible = !poly.visible;
            // paperjs shows handles for invisible items :(
            // TODO: use layers?
            if (!poly.visible && poly.selected) poly.selected = false;
            if (poly.visible && this.lines[i].selected) poly.selected = true;
        }
    }
    
    addToSelection(line) {
        if (this.selection.indexOf(line) == -1) this.selection.push(line);
        this.deleteLineBtn.style.left = line.baselinePath.bounds.topRight.x + 20 + "px";
        this.deleteLineBtn.style.top = line.baselinePath.bounds.topRight.y -30 + "px";
        this.deleteLineBtn.style.display = 'inline';
    }
    removeFromSelection(line) {
        this.deleteLineBtn.style.display = 'none';
        this.selection.pop(this.selection.indexOf(line));
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
        paper.view.viewSize = [this.img.innerWidth(), this.img.innerHeight()];
    }
    
    load(data) {
        data.forEach(function(line) {
            let newLine = this.createLine(line);
            newLine.createPolygon();
        }.bind(this));
    }

    selectionRectangle(event) {
        if (!this.clip) {
            let shape = new Rectangle([event.point.x, event.point.y], [1, 1]);
            this.clip = new Path.Rectangle(shape, 0);
            this.clip.opacity = 1;
            this.clip.strokeWidth = 2;
            this.clip.strokeColor = 'grey';
            this.clip.dashArray = [10, 4];
            this.clip.originalPoint = event.point;
        } else {
            this.clip.bounds.width = Math.max(1, Math.abs(this.clip.originalPoint.x - event.point.x));
            if (event.point.x > this.clip.originalPoint.x) {
                this.clip.bounds.x = this.clip.originalPoint.x;
            } else {
                this.clip.bounds.x = event.point.x;
            }
            this.clip.bounds.height = Math.max(1, Math.abs(this.clip.originalPoint.y - event.point.y));
            if (event.point.y > this.clip.originalPoint.y) {
                this.clip.bounds.y = this.clip.originalPoint.y;
            } else {
                this.clip.bounds.y = event.point.y;
            }
        }
    }
    
    lassoSelection(event) {
        // draws a rectangle lasso selection tool that selects every line it crosses
        this.selectionRectangle(event);
        for (let i in this.lines) {
            let line = this.lines[i];
            if (line.selected) {continue;}  // avoid calculs
            if (this.clip.intersects(line.baselinePath) ||
                line.baselinePath.isInside(this.clip.bounds)) {
                line.select();
            }
        }
    }

    splitTool(event) {
        this.selectionRectangle(event);
        this.lines.forEach(function(line) {
            let intersections = line.baselinePath.getIntersections(this.clip);
            for (var i = 0; i < intersections.length; i++) {
                // cut locations helper
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
                        if (this.clip.contains(segment.point)) {
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
                    line.changed = true;
                } else {
                    let newLine = line.baselinePath.splitAt(intersections[i+1]);
                    let nl = this.createLine(newLine);
                    let trash = line.baselinePath.splitAt(intersections[i]);
                    line.polygonPath.removeSegments();
                    line.createPolygon();
                    nl.createPolygon();
                    line.changed = true;
                    line = nl;
                    trash.remove();
                }
            }
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
        this.selection[0].polygonPath.removeSegments();
        this.selection[0].createPolygon();
        this.selection[0].changed = true;
    }
    
    getColors() {
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

        if (ColorThief !== undefined) {
            var colorThief = new ColorThief();
            let palette = colorThief.getPalette(this.img, 5);
            for (let i in palette) {
                let el = document.getElementById('color'+i);
                el.style.backgroundColor = rgbToHex(palette[i]);
                el.style.padding = '10px';
            }
            let choices = chooseColors(palette);
            this.mainColor = choices[0];
            this.secondaryColor = choices[1];
        } else {
            this.mainColor = 'blue';
            this.secondaryColor = 'teal';
        }
    }
}
