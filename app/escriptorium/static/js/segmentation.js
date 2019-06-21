/*
Baseline segmenter
*/

class Line {
    constructor(segments, segmenter_) {
        this.deleting = null;
        this.segmenter = segmenter_;
        
        var line_ = this;  // save in scope
        this.path = new Path({
            strokeColor: segmenter_.mainColor,
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
                this.smooth({ type: 'catmull-rom', 'factor': 0.5 });
            }
        });
        this.path.line = this;  // necessary for multi selector intersection
        
        segmenter_.purgeSelection();
        this.$deleteBtn = $('#delete-line').clone().appendTo($('#delete-line').parent());
        this.$deleteBtn.click($.proxy(function(event) {
            this.delete();
        }, this));
    }

    select() {
        this.path.selected = true;
        this.path.strokeColor = this.segmenter.secondaryColor;
        this.$deleteBtn.css({
            left: this.path.bounds.topRight.x + 20,
            top: this.path.bounds.topRight.y -30
        }).show();
        this.segmenter.addToSelection(this);
    }

    unselect() {
        this.path.selected = false;
        this.path.strokeColor = this.segmenter.mainColor;
        this.$deleteBtn.hide();
        if (this.segmenter.deleting && this.segmenter.deleting.path == this.path) {
            $('#delete-point').hide();
        }
        this.segmenter.removeFromSelection(this);
    }

    delete() {
        this.unselect();
        this.segmenter.paths.pop(this.segmenter.paths.indexOf(this.path));
        this.path.remove();
    }
}

class Segmenter {
    constructor(canvas, img, length_treshold=10) {
        this.canvas = canvas;
        this.paths = [];
        this.selection = [];
        // the minimal length in pixels below which the line will be removed automatically
        this.length_threshold = length_treshold;
        
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
                if (this.newLine.path.length < this.length_treshold) {
                    if (DEBUG) console.log('Erasing bogus line of length ' + this.newLine.path.length);
                    this.newLine.delete();
                }
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
