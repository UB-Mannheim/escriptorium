class Line {
    constructor(segments, segmenter_) {
        this.deleting = null;
        this.segmenter = segmenter_;

        var line_ = this;  // save in scope
        this.path = new Path({
            strokeColor: 'blue',
            strokeWidth: 10,
            opacity: 0.6,
            selected: false,
            onMouseDown: function(event) {
                if (!event.event.shiftKey && !event.event.ctrlKey) {
                    segmenter_.purgeSelection();
                }
                var hit = this.hitTest(event.point, {
	                segments: true,
	                stroke: true,
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
                line_.select();
                segmenter_.draggingPoint = this.getNearestLocation(event.point).segment.point;
            },
            onDoubleClick: function(event) {
                var location = this.getNearestLocation(event.point);
                this.insert(location.index+1, location);
                this.smooth();
            }
        });
        this.path.line = this;  // necessary for multi selector intersection
        segmenter_.purgeSelection();
        this.$deleteBtn = $('#delete-line').clone().appendTo($('#delete-line').parent());
        this.$deleteBtn.click($.proxy(function(event) {
            this.unselect();
            this.delete();
        }, this));
    }

    static fromEvent(event, segmenter_) {
        return new Line([event.point], segmenter_);
    }

    select() {
        this.path.selected = true;
        this.path.strokeColor = 'teal';
        this.$deleteBtn.css({
            left: this.path.bounds.topRight.x + 20,
            top: this.path.bounds.topRight.y -30
        }).show();
        this.segmenter.addToSelection(this);
    }

    unselect() {
        this.path.selected = false;
        this.path.strokeColor = 'blue';
        this.$deleteBtn.hide();
        if (this.segmenter.deleting && this.segmenter.deleting.path == this.path) {
            $('#delete-point').hide();
        }
        this.segmenter.removeFromSelection(this);
    }

    delete() {
        this.segmenter.paths.pop(this.segmenter.paths.indexOf(this.path));
        this.path.remove();
    }
}

class Segmenter {
    constructor(canvas) {
        this.canvas = canvas;
        this.paths = [];
        this.selection = [];
        
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
                this.newLine.path.add(event.point);
		    } else if (event.event.ctrlKey) {
                // multi move
                for (let i in this.selection) {
                    for(let j in this.selection[i].path.segments) {
                        let point = this.selection[i].path.segments[j].point;
                        point.x += event.delta.x;
                        point.y += event.delta.y;
                    }
                }
            } else if (event.event.shiftKey) {
                // multi selection
                if (!this.clip) {
                    let shape = new Rectangle([event.point.x, event.point.y], [1, 1]);
                    this.clip = new Path.Rectangle(shape, 0);
                    this.clip.opacity = 0.3;
                    this.clip.strokeWidth = 2;
                    this.clip.strokeColor = 'black';
                    this.clip.dashArray = [10, 4];
                } else {
                    if (this.clip.bounds.width + event.delta.x > 0) {
                        this.clip.bounds.width += event.delta.x;
                    } else {
                        this.clip.bounds.x -= event.delta.x;
                    }
                    if (this.clip.bounds.height + event.delta.y > 0) {
                        this.clip.bounds.height += event.delta.y;
                    } else {
                        this.clip.bounds.y += event.delta.y;
                        this.clip.bounds.height += Math.abs(event.delta.y);
                    }
                    for (let i in this.paths) {
                        let inBounds = this.clip.getIntersections(this.paths[i]);
                        if (inBounds.length) {
                            this.paths[i].line.select();
                        }
                    }
                }
            } else if (this.dragging) {
			    this.draggingPoint.x += event.delta.x;
			    this.draggingPoint.y += event.delta.y;
            } else if (event.event.altKey) {
                // view.rotate(0.1);
            } else if (!this.newLine) {
                this.newLine = this.createLine(event);
            } 
        }, this);

        tool.onMouseUp = $.proxy(function(event) {
            this.dragging = null;
            if (this.newLine) {
                this.newLine.path.simplify(12);
                this.newLine = null;
            }
            if (this.clip) {
                this.clip.remove();
                this.clip = null;
            }
        }, this);

        $('#delete-point').click($.proxy(function(event) {
            if (this.deleting) {
                this.deleting.path.removeSegment(this.deleting.index);
                $('#delete-point').hide();
                this.deleting = null;
            }
            return false;
        }, this));
    }

    createLine(event) {
        this.purgeSelection();
        var line = Line.fromEvent(event, this);
        this.paths.push(line.path);
        return line;
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
}
