/*
Baseline segmenter
*/

class Line {
    constructor(segments, segmenter_) {
        this.segmenter = segmenter_;

        this.polygon = null;
        
        var line_ = this;  // save in scope

        this.polygon = new Path({
            closed: true,
            opacity: 0.1,
            fillColor: this.segmenter.mainColor,
            visible: this.segmenter.showPolygons,
            onMouseDown: function(event) {
                segmenter_.dragging = this;
                segmenter_.draggingPoint = this.getNearestLocation(event.point).segment;
                if (!event.event.shiftKey && !event.event.ctrlKey) {
                    segmenter_.purgeSelection();
                }
                line_.select();
                $('#delete-point').hide();
            }
        });
        
        this.baseline = new Path({
            strokeColor: segmenter_.mainColor,
            strokeWidth: 12,
            opacity: 0.5,
            selected: false,
            onMouseDown: function(event) {
                if (!event.event.shiftKey && !event.event.ctrlKey) {
                    segmenter_.purgeSelection();
                }
                line_.select();
                var hit = this.hitTest(event.point, {
	                segments: true,
	                tolerance: 5
                });
                if (hit && hit.type=='segment' &&
                    hit.segment.index != 0 &&
                    hit.segment.index != hit.segment.path.segments.length-1) {
                    $('#delete-point').css({
                        left: hit.segment.point.x - $('#delete-point').width() / 2,
                        top: hit.segment.point.y - $('#delete-point').height() - 20
                    }).show();
                    segmenter_.deleting = hit.segment;
                } else {
                    $('#delete-point').hide();
                }
                segmenter_.dragging = this;
                segmenter_.draggingPoint = this.getNearestLocation(event.point).segment;
            },
            onDoubleClick: function(event) {
                let location = this.getNearestLocation(event.point);
                let newSegment = this.insert(location.index+1, location);
                this.smooth({ type: 'catmull-rom', 'factor': 0.5 });
                line_.createPolygonEdgeForBaselineSegment(newSegment);
            }
        });
        this.baseline.line = this;  // necessary for multi selector intersection
        
        segmenter_.purgeSelection();
        this.$deleteBtn = $('#delete-line').clone().appendTo($('#delete-line').parent());
        this.$deleteBtn.click($.proxy(function(event) {
            this.delete();
        }, this));
    }

    createPolygonEdgeForBaselineSegment(segment) {
        let pt = segment.point;
        let upperVector = new Point({ angle: pt.angle - 90, length: 20 });
        this.polygon.insert(segment.index, pt.add(upperVector));

        let lowerVector = new Point({ angle: pt.angle + 90, length: 10 });
        this.polygon.insert(this.polygon.segments.length-segment.index, pt.add(lowerVector));
    }
    deletePolygonsEdgeForBaselineSegment(segment) {
        this.polygon.removeSegment(this.polygon.segments.length-segment.index-1);
        this.polygon.removeSegment(segment.index);
    }
    
    createPolygon() {
        for (let i in this.baseline.segments) {
            this.createPolygonEdgeForBaselineSegment(this.baseline.segments[i]);
        }        
    }

    recreatePolygon() {
        if (this.polygon) this.polygon.removeSegments();
        this.createPolygon();
    }
    
    select() {
        if (this.polygon && this.polygon.visible) this.polygon.selected = true;
        this.baseline.selected = true;
        this.baseline.strokeColor = this.segmenter.secondaryColor;
        this.$deleteBtn.css({
            left: this.baseline.bounds.topRight.x + 20,
            top: this.baseline.bounds.topRight.y -30
        }).show();
        this.segmenter.addToSelection(this);
    }

    unselect() {
        if (this.polygon) this.polygon.selected = false;
        this.baseline.selected = false;
        this.baseline.strokeColor = this.segmenter.mainColor;
        this.$deleteBtn.hide();
        if (this.segmenter.deleting && this.segmenter.deleting.path == this.baseline) {
            $('#delete-point').hide();
        }
        this.segmenter.removeFromSelection(this);
    }

    delete() {
        this.unselect();
        this.segmenter.paths.pop(this.segmenter.paths.indexOf(this.baseline));
        this.baseline.remove();
        this.polygon.remove();
    }
}

class Segmenter {
    constructor(canvas, img, length_treshold=10) {
        this.canvas = canvas;
        this.paths = [];
        this.selection = [];
        // the minimal length in pixels below which the line will be removed automatically
        this.length_threshold = length_treshold;
        this.showPolygons = false;
        
        // needed?
        this.newLine = null;
        this.dragging = null;
        this.draggingPoint = null;
        this.deleting = null;
        this.clip = null;  // draw a box for multi selection
        
        // init paperjs
        paper.install(window);
        paper.settings.handleSize = 10;
        paper.setup(this.canvas);
        var tool = new Tool();

        this.getColors(img);
        
        tool.onMouseDown = $.proxy(function(event) {
            if (!this.dragging) {
                $('#delete-point').hide();
                this.deleting = null;
                if (!event.event.shiftKey && !event.event.ctrlKey) {
                    this.purgeSelection();
                }
            }
        }, this);

        tool.onMouseDrag = $.proxy(function(event) {
            if (this.newLine) {
                // adding points to current line
                this.newLine.baseline.add(event.point);
		    } else if (event.event.ctrlKey) {
                // multi move
                for (let i in this.selection) {
                    for(let j in this.selection[i].baseline.segments) {
                        let point = this.selection[i].baseline.segments[j].point;
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

                    for (let i in this.paths) {
                        if (this.paths[i].selected) {continue;}  // avoid calculs
                        if (this.clip.intersects(this.paths[i]) || this.paths[i].isInside(this.clip.bounds)) {
                            this.paths[i].line.select();
                        }
                    }
                }
            } else if (this.dragging) {
                // move closest point
			    this.draggingPoint.point.x += event.delta.x;
			    this.draggingPoint.point.y += event.delta.y;
                if (this.dragging.line) {
                    let poly = this.dragging.line.polygon;
                    if (poly) {
                        let top = poly.segments[this.dragging.line.baseline.segments.length*2 - this.draggingPoint.index - 1].point;
                        let bottom = poly.segments[this.draggingPoint.index].point;
                        top.x += event.delta.x;
                        top.y += event.delta.y;
                        bottom.x += event.delta.x;
                        bottom.y += event.delta.y;
                    }
                }
            } else if (event.event.altKey) {
                // view.rotate(0.1);
            } else if (!this.newLine) {
                this.newLine = this.createLine(event);
            } 
        }, this);

        tool.onMouseUp = $.proxy(function(event) {
            this.dragging = null;
            if (this.newLine) {
                if (this.newLine.baseline.length < this.length_treshold) {
                    if (DEBUG) console.log('Erasing bogus line of length ' + this.newLine.baseline.length);
                    this.newLine.delete();
                }
                this.newLine.baseline.simplify(12);
                this.newLine.createPolygon();
                this.newLine = null;
            }
            if (this.clip) {
                this.clip.remove();
                this.clip = null;
            }
        }, this);

        $('#delete-point').click($.proxy(function(event) {
            if (this.deleting) {
                let line = this.deleting.path.line;
                line.deletePolygonsEdgeForBaselineSegment(this.deleting);
                this.deleting.remove();
                $('#delete-point').hide();
                this.deleting = null;
            }
            return false;
        }, this));

        $('#toggle-polygons').click($.proxy(function(event) {
            this.togglePolygons();
        }, this));

        $(document).on('keyup', $.proxy(function(event) {
            if (event.keyCode == 46)  { // supr
                for (let i=this.selection.length-1; i >= 0; i--) {    
                    this.selection[i].delete();
                }
            }
        }, this));
    }

    createLine(event) {
        this.purgeSelection();
        var line = new Line([event.point], this);
        this.paths.push(line.baseline);
        return line;
    }

    togglePolygons() {
        this.showPolygons = !this.showPolygons;
        for (let i in this.paths) {
            let poly = this.paths[i].line.polygon;
            poly.visible = !poly.visible;
            // paperjs shows handles for invisible items :(
            if (!poly.visible && poly.selected) poly.selected = false;
            if (poly.visible && this.paths[i].line.baseline.selected) poly.selected = true;
        }
    }
        
    addToSelection(line) {
        this.selection.push(line);
    }
    removeFromSelection(line) {
        this.selection.pop(this.selection.indexOf(line));
    }
    purgeSelection() {
        for (let i=this.selection.length-1; i >= 0; i--) {
            this.selection[i].unselect();
        }
        this.selection = [];
    }

    getColors(img) {
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
        
        var colorThief = new ColorThief();
        let palette = colorThief.getPalette(img, 5);
        if (DEBUG) {
            for (let i in palette) {
                $('#color'+i).css({backgroundColor: rgbToHex(palette[i]), padding: '10px'});
            }
        }
        let choices = chooseColors(palette);
        this.mainColor = choices[0];
        this.secondaryColor = choices[1];
    }
}
