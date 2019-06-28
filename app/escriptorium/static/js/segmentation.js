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

  newLineCallback
  updateLineCallback
  deleteLineCallback

segmenter.load(lines)

*/

class SegmenterRegion {}

class SegmenterLine {
    constructor(baseline, polygon, segmenter_) {
        this.segmenter = segmenter_;
        this.baseline = baseline;
        this.polygon = null;
        this.changed = false;
        this.selected = false;
        
        var line_ = this;  // save in scope

        this.polygonPath = new Path({
            closed: true,
            opacity: 0.1,
            fillColor: this.segmenter.mainColor,
            visible: this.segmenter.showPolygons,
            segments: this.polygon,
            onMouseDown: function(event) {
                segmenter_.dragging = line_;
                segmenter_.draggingPoint = this.getNearestLocation(event.point).segment;
                if (event.event.shiftKey) {
                    line_.toggleSelect();
                } else if (!event.event.shiftKey && !event.event.ctrlKey) {
                    segmenter_.purgeSelection();
                    line_.select();
                } else {
                    line_.select();
                }
            }
        });
        
        this.baselinePath = new Path({
            strokeColor: segmenter_.mainColor,
            strokeWidth: 12,
            opacity: 0.5,
            segments: this.baseline,
            selected: false,
            visible: (this.segmenter.mode == 'click'),
            onMouseDown: function(event) {
                line_.segmenter.dragging = line_;
                line_.segmenter.draggingPoint = this.getNearestLocation(event.point).segment;
                if (event.event.shiftKey) {
                    line_.toggleSelect();
                } else if (!event.event.shiftKey && !event.event.ctrlKey) {
                    segmenter_.purgeSelection();
                    line_.select();
                } else {
                    line_.select();
                }
                    
                var hit = this.hitTest(event.point, {
	                segments: true,
	                tolerance: 5
                });
                if (hit && hit.type=='segment' &&
                    hit.segment.index != 0 &&
                    hit.segment.index != hit.segment.path.segments.length-1) {

                    // right click
                    
                    line_.segmenter.deletePointBtn.style.left = hit.segment.point.x - 20 + 'px';
                    line_.segmenter.deletePointBtn.style.top = hit.segment.point.y - 40 + 'px';
                    line_.segmenter.deletePointBtn.style.display = 'inline';
                    line_.segmenter.deleting = hit.segment;
                } else {
                    line_.segmenter.deletePointBtn.style.display = 'none';
                }

            },
            onDoubleClick: function(event) {
                let location = this.getNearestLocation(event.point);
                let newSegment = this.insert(location.index+1, location);
                this.smooth({ type: 'catmull-rom', 'factor': 0.5 });
                line_.createPolygonEdgeForBaselineSegment(newSegment);
            }
        });
        this.baselinePath.line = this;  // necessary for multi selector intersection
        
        this.segmenter.purgeSelection();
    }

    createPolygonEdgeForBaselineSegment(segment) {
        let pt = segment.point;
        let upperVector = new Point({ angle: pt.angle - 90, length: 20 });
        this.polygonPath.insert(segment.index, pt.add(upperVector));

        let lowerVector = new Point({ angle: pt.angle + 90, length: 10 });
        this.polygonPath.insert(this.polygonPath.segments.length-segment.index, pt.add(lowerVector));
    }
    deletePolygonsEdgeForBaselineSegment(segment) {
        this.polygonPath.removeSegment(this.polygonPath.segments.length-segment.index-1);
        this.polygonPath.removeSegment(segment.index);
    }
    
    createPolygon() {
        for (let i in this.baselinePath.segments) {
            this.createPolygonEdgeForBaselineSegment(this.baselinePath.segments[i]);
        }
    }
    
    select() {
        if (this.selected) return;
        if (this.polygonPath && this.polygonPath.visible) this.polygonPath.selected = true;
        this.baselinePath.selected = true;
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

    extend(point) {
        if (this.baselinePath.length > this.segmenter.lengthThreshold) {
            this.baselinePath.visible = true;
        }
        return this.baselinePath.add(point);
    }
    
    close() {
        // call when drawing the last point of the line
        if (this.segmenter.mode == 'drag') {
            this.baselinePath.simplify(12);
        }
        this.createPolygon();
    }
    
    delete() {
        this.unselect();
        this.segmenter.lines.pop(this.segmenter.lines.indexOf(this));
        this.baselinePath.remove();
        this.polygonPath.remove();
        // TODO: trigger event or callback
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

        this.mode = 'drag';  // drag or click
        
        // needed?
        this.newLine = null;
        this.dragging = null;
        this.draggingPoint = null;
        this.deleting = null;
        this.clip = null;  // draw a box for multi selection

        this.deletePointBtn = document.getElementById('delete-point');
        this.deleteLineBtn = document.getElementById('delete-line');
        this.togglePolygonsBtn = document.getElementById('toggle-polygons');
        
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
            if (this.mode == 'click' && !event.event.ctrlKey && !event.event.shiftKey) {
                if (!this.newLine) {
                    if (!this.dragging) { 
                        var pt;
                        this.newLine = this.createLine(event);
                        pt = this.newLine.extend(event.point);
                        this.dragging = pt;
                        this.draggingPoint = pt.point;
                    }
                } else if (this.mode == 'click' &&
                           (event.event.which === 3 || event.event.button === 2)) {
                    // right click, end the line
                    this.newLine.close();
                    this.newLine = null;
                    this.dragging = null;
                    this.draggingPoint = null;
                } else {
                    pt = this.newLine.extend(event.point);
                    this.dragging = pt;
                    this.draggingPoint = pt.point;
                }
            }
            if (!this.dragging) {
                this.deleting = null;
                if (!event.event.shiftKey && !event.event.ctrlKey) {
                    this.purgeSelection();
                }
            }
            if (!this.deleting) {
                this.deletePointBtn.style.display = 'none';
            }
        }.bind(this);

        tool.onMouseMove = function(event) {
            if (this.mode == 'click' && this.dragging && this.draggingPoint) {
			    this.draggingPoint.x += event.delta.x;
			    this.draggingPoint.y += event.delta.y;
            }
        }.bind(this);
        
        tool.onMouseDrag = function(event) {
            if (this.mode == 'drag' && this.newLine) {
                // adding points to current line
                var pt = this.newLine.extend(event.point);
                this.dragging = pt;
		    } else if (event.event.ctrlKey) {
                // multi move
                for (let i in this.selection) {
                    for(let j in this.selection[i].baselinePath.segments) {
                        let point = this.selection[i].baselinePath.segments[j].point;
                        point.x += event.delta.x;
                        point.y += event.delta.y;
                    }
                }
            } else if (event.event.shiftKey) {
                // multi lasso selection
                if (!this.clip) {
                    let shape = new Rectangle([event.point.x, event.point.y], [1, 1]);
                    this.clip = new Path.Rectangle(shape, 0);
                    this.clip.opacity = 0.3;
                    this.clip.strokeWidth = 2;
                    this.clip.strokeColor = 'black';
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

                    for (let i in this.lines) {
                        let line = this.lines[i];
                        if (line.selected) {continue;}  // avoid calculs
                        if (this.clip.intersects(line.baselinePath) ||
                            line.baselinePath.isInside(this.clip.bounds)) {
                            line.select();
                        }
                    }
                }
            } else if (this.dragging) {
                // move closest point
			    this.draggingPoint.point.x += event.delta.x;
			    this.draggingPoint.point.y += event.delta.y;
                let poly = this.dragging.polygonPath;
                if (poly) {
                    let top = poly.segments[this.dragging.baselinePath.segments.length*2 -
                                            this.draggingPoint.index - 1].point;
                    let bottom = poly.segments[this.draggingPoint.index].point;
                    top.x += event.delta.x;
                    top.y += event.delta.y;
                    bottom.x += event.delta.x;
                    bottom.y += event.delta.y;
                }
            } else if (event.event.altKey) {
                // view.rotate(0.1);
            } else if (!this.newLine && this.mode == 'drag') {
                this.newLine = this.createLine(event);
            }
        }.bind(this);

        tool.onMouseUp = function(event) {
            if (this.mode == 'drag') {
                if (this.newLine) {
                    if (this.newLine.baselinePath.length < this.length_threshold) {
                        if (DEBUG) console.log('Erasing bogus line of length ' + this.newLine.baselinePath.length);
                        this.newLine.delete();
                    }
                    this.newLine.close();
                    this.newLine = null;
                }
            }
            if (!this.newLine) {
                this.dragging = null;
                this.draggingPoint = null;
            }
            if (this.clip) {
                this.clip.remove();
                this.clip = null;
            }
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
            }
        }.bind(this));
    }
    
    createLine(event) {
        // this.purgeSelection();
        var line = new SegmenterLine([event.point], null, this);
        this.lines.push(line);
        return line;
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
        this.selection.push(line);
        this.deleteLineBtn.style.left = line.baselinePath.bounds.topRight.x + 20 + "px";
        this.deleteLineBtn.style.top = line.baselinePath.bounds.topRight.y -30 + "px";
        this.deleteLineBtn.style.display = 'inline';
    }
    removeFromSelection(line) {
        this.deleteLineBtn.style.display = 'none';
        this.selection.pop(this.selection.indexOf(line));
    }
    purgeSelection() {
        for (let i=this.selection.length-1; i >= 0; i--) {
            this.selection[i].unselect();
        }
        this.selection = [];
    }

    resetViewSize() {
        paper.view.viewSize = [this.img.innerWidth(), this.img.innerHeight()];
    }

    toggleMode() {
        this.mode = this.mode=='click'?'drag':'click';
    }
    
    load(data) {
        // TODO
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
