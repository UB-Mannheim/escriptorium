
class SegmenterLine {
    constructor(type, pk, baseline, polygon, segmenter_) {  // imgRatio, 
        this.type = type; // can be either 'block' or 'line'
        this.pk = pk;
        this.baseline = baseline;
        this.polygon = polygon;
        this.segmenter = segmenter_; // todo: remove
        // this.updateApi();
        // this.order = obj.order;
        // this.block = this.part.blocks.find(function(block) {
        //     return block.pk == obj.block;
        // });
        // this.setRatio(imgRatio);
        this.changed = false;
        this.selected = false;
        // this.click = {x: null, y:null};
        // this.originalWidth = (obj.box[2] - obj.box[0]) * this.ratio;
        // this.$container = $('#seg-panel .img-container');
        // var $box = $('<div class="box '+this.type+'-box"> <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>'+(DEBUG?this.order:'')+'</div>');
        
        var line_ = this;  // save in scope

        this.polygonPath = new Path({
            closed: true,
            opacity: 0.1,
            fillColor: this.segmenter.mainColor,
            visible: this.segmenter.showPolygons,
            segments: this.polygon,
            // applyMatrix: false,
            onMouseDown: function(event) {
                segmenter_.dragging = this;
                segmenter_.draggingPoint = this.getNearestLocation(event.point).segment;
                if (event.event.shiftKey) {
                    line_.toggleSelect();
                } else if (!event.event.shiftKey && !event.event.ctrlKey) {
                    segmenter_.purgeSelection();
                    line_.select();
                } else {
                    line_.select();
                }
                $('#delete-point').hide();
            }
        });
        
        this.baselinePath = new Path({
            strokeColor: segmenter_.mainColor,
            strokeWidth: 12,
            opacity: 0.5,
            selected: false,
            segments: this.baseline,
            // applyMatrix: false,
            onMouseDown: function(event) {
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
        this.baselinePath.line = this;  // necessary for multi selector intersection

        this.$deleteBtn = $('#delete-line').clone().appendTo($('#delete-line').parent());
        this.$deleteBtn.click($.proxy(function(event) {
            this.delete();
        }, this));

        // $box.data('Box', this);
        // $box.appendTo($('#seg-panel .img-container .zoom-container'));
        // this.$element = $box;
        // this.setPosition();
    }
    
    updateApi() {
        var part_api = API.part.replace('{part_pk}', this.part.pk);
        this.api = {
            list: part_api + this.type + 's' + '/'
        };
        if (this.pk) {
            this.api.detail = this.api.list + this.pk + '/';
        }
    }
    
    setRatio(ratio) {
        this.ratio = ratio;
    }
    
    showOverlay() {
        // TODO
        // $('.panel .overlay').css({
        //     left: this.box[0]*this.ratio + 'px',
        //     top: this.box[1]*this.ratio + 'px',
        //     width: (this.box[2] - this.box[0])*this.ratio + 'px',
        //     height: (this.box[3] - this.box[1])*this.ratio + 'px'
        // }).show();
    }

    createPolygonEdgeForBaselineSegment(segment) {
        let pt = segment.point;
        let upperVector = new Point({ angle: pt.angle - 90, length: 20 });
        this.polygonPath.insert(segment.index, pt.add(upperVector));

        let lowerVector = new Point({ angle: pt.angle + 90, length: 10 });
        this.polygonPath.insert(this.polygonPath.segments.length-segment.index, pt.add(lowerVector));
    }
    deletePolygonsEdgeForBaselineSegment(segment) {
        this.polygonPath.removeSegment(this.polygon.segments.length-segment.index-1);
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
        this.$deleteBtn.css({
            left: this.baselinePath.bounds.topRight.x + 20,
            top: this.baselinePath.bounds.topRight.y -30
        }).show();
        this.segmenter.addToSelection(this);
        this.selected = true;
    }
    unselect() {
        if (!this.selected) return;
        if (this.polygonPath) this.polygonPath.selected = false;
        this.baselinePath.selected = false;
        this.baselinePath.strokeColor = this.segmenter.mainColor;
        this.$deleteBtn.hide();
        if (this.segmenter.deleting && this.segmenter.deleting.path == this.baselinePath) {
            $('#delete-point').hide();
        }
        this.segmenter.removeFromSelection(this);
        this.selected = false;
        
        if (this.changed) {
            this.save();
        }
    }
    toggleSelect() {
        if (this.selected) this.unselect();
        else this.select();
    }
    
    save() {
        var post = {};
        post = { document_part: this.part.pk,
                 box: JSON.stringify(this.getBox()) };
        if (this.type == 'line') post.block = this.block?this.block.pk:null;
        var uri = this.pk?this.api.detail:this.api.list;
        var type = this.pk?'PUT':'POST';

        $.ajax({url: uri, type: type, data: post})
            .done($.proxy(function(data) {
                /* create corresponding transcription line */
                if (!this.pk && this.type == 'line') { panels['trans'].addLine(data); }
                Object.assign(this, data);  // TODO: checks ?
                this.updateApi();
            }, this)).fail(function(data){
                alert("Couldn't save block:", data);
            });
        this.changed = false;
    }
    delete() {
        if (!confirm("Do you really want to delete this line and all of its transcriptions?")) { return; }
        this.unselect();
        this.segmenter.lines.pop(this.segmenter.lines.indexOf(this));
        this.baselinePath.remove();
        this.polygonPath.remove();
        if (this.pk !== null) {
            $.ajax({url: this.api.detail, type:'DELETE'});
        }
        if (this.type == 'line') {
            var tl = $('#trans-box-line-'+this.pk).data('TranscriptionLine');
            if (tl) tl.delete();
        }
    }
}

class Segmenter {
    constructor(img, length_treshold=10) {
        this.img = img;
        this.canvas = $('<canvas resize>').css({
            position: 'absolute', left: 0, transformOrigin: 'top left',
            minWidth: '10px', minHeight: '10px'
        }).insertAfter(this.img);
        this.lines = [];
        this.selection = [];
        // the minimal length in pixels below which the line will be removed automatically
        this.length_threshold = length_treshold;
        this.showPolygons = true;
        
        // needed?
        this.newLine = null;
        this.dragging = null;
        this.draggingPoint = null;
        this.deleting = null;
        this.clip = null;  // draw a box for multi selection

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
        // var ratio = this.img.width() / this.part.image.size[0];
        var line = new SegmenterLine('line', null, [event.point], null, this);
        this.lines.push(line);
        return line;
    }

    togglePolygons() {
        this.showPolygons = !this.showPolygons;
        for (let i in this.lines) {
            let poly = this.lines[i].polygonPath;
            poly.visible = !poly.visible;
            // paperjs shows handles for invisible items :(
            if (!poly.visible && poly.selected) poly.selected = false;
            if (poly.visible && this.lines[i].baselinePath.selected) poly.selected = true;
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
        
        var colorThief = new ColorThief();
        let palette = colorThief.getPalette(this.img.get(0), 5);
        if (DEBUG) {
            for (let i in palette) {
                $('#color'+i).css({backgroundColor: rgbToHex(palette[i]), padding: '10px'});
            }
        }
        let choices = chooseColors(palette);
        this.mainColor = choices[0];
        this.secondaryColor = choices[1];
    }

    initPaperJs() {
        paper.install(window);
        paper.settings.handleSize = 10;
        paper.setup(this.canvas.get(0));
        var tool = new Tool();

        paper.view.onResize = $.proxy(function(event) {
            // rescale every element in the canvas :/
            let ratio = event.size.width / (event.size.width - event.delta.width);
            for (let i in this.lines) {
                this.lines[i].baselinePath.scale(ratio, [0, 0]);
                this.lines[i].polygonPath.scale(ratio, [0, 0]);
            }
        }, this);
        
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
                this.newLine.baselinePath.add(event.point);
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
                        if (this.lines[i].selected) {continue;}  // avoid calculs
                        if (this.clip.intersects(this.lines[i].baselinePath) || this.lines[i].baselinePath.isInside(this.clip.bounds)) {
                            this.lines[i].select();
                        }
                    }
                }
            } else if (this.dragging) {
                // move closest point
			    this.draggingPoint.point.x += event.delta.x;
			    this.draggingPoint.point.y += event.delta.y;
                if (this.dragging.line) {
                    let poly = this.dragging.line.polygonPath;
                    if (poly) {
                        let top = poly.segments[this.dragging.line.baselinePath.segments.length*2 - this.draggingPoint.index - 1].point;
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
                if (this.newLine.baselinePath.length < this.length_treshold) {
                    if (DEBUG) console.log('Erasing bogus line of length ' + this.newLine.baselinePath.length);
                    this.newLine.delete();
                }
                this.newLine.baselinePath.simplify(12);
                this.newLine.createPolygon();
                this.newLine = null;
            }
            if (this.clip) {
                this.clip.remove();
                this.clip = null;
            }
        }, this);

        zoom.events.on('wheelzoom.updated', $.proxy(function(event, data) {
            this.img.css('transform',
                         'translate('+(data.pos.x)+'px,'+(data.pos.y)+'px) '+
                         'scale('+data.scale+')');
            
            this.canvas.css({top: data.pos.y,
                             left: data.pos.x});

            paper.view.viewSize = [this.img.innerWidth(), this.img.innerHeight()];
            // paper.view.zoom = data.scale;
            // paper.view.translate(data.delta.pos);

            //
            for (let i in this.lines) {

                this.lines[i].baselinePath.scale(data.delta.scale, [0, 0]);
                // this.lines[i].baselinePath.translate(data.delta.pos);
                this.lines[i].polygonPath.scale(data.delta.scale, [0, 0]);
                // this.lines[i].polygonPath.translate(data.delta.pos); 
            }
            // console.log(data.delta.pos, data.scale);
            // paper.view.translate(data.delta.pos);
            // paper.view.zoom = data.scale;
        }, this));
    }

    reset() {
        if (this.part) {
            paper.view.viewSize = [this.img.innerWidth(), this.img.innerHeight()];
        }
    }
    
    load(part) {
        this.part = part;
        for (let i=this.lines.length-1; i >= 0; i--) {    
            this.lines[i].delete();
        }

        this.getColors();

        var ratio = this.img.width() / part.image.size[0];
        function toRatio(pt) {
            return pt;
            return [pt[0]*ratio, pt[1]*ratio];
        }

        this.initPaperJs();

        for (let i in part.lines) {
            let l = part.lines[i];
            let line = new SegmenterLine('line', l.pk,
                                         l.baseline?l.baseline.map(toRatio):null,
                                         l.polygon?l.polygon.map(toRatio):null,
                                         this);
            this.lines.push(line);
        }


    }
}


class SegmentationPanel extends Panel {
    constructor ($panel, $tools, opened) {
        super($panel, $tools, opened);
        this.seeBlocks = true;
        this.seeLines = true;

        // zoom.register(this.$container, true);
        this.segmenter = new Segmenter($('img', this.$container));
        
        $('#viewer-blocks', this.$panel).click($.proxy(function(ev) {
            
        }, this));
        $('#viewer-lines', this.$panel).click($.proxy(function(ev) {
            this.segmenter.togglePolygons();
        }, this));
    }
    
    showBlocks() {
        Object.keys(this.part.blocks).forEach($.proxy(function(i) {
            this.boxes.push(new Box('block', this.part, this.part.blocks[i], this.ratio));
        }, this));
        if (!this.seeBlocks) $('.block-box').hide();
    }
    showLines() {
        Object.keys(this.part.lines).forEach($.proxy(function(i) {
            this.boxes.push(new Box('line', this.part, this.part.lines[i], this.ratio));
        }, this));
        if (!this.seeLines) $('.line-box').hide();
    }
    
    load(part) {
        super.load(part);

        // zoom.register(this.$container, true);
        
        if (this.part.image.thumbnails) {
            $('img', this.$container).attr('src', this.part.image.thumbnails.large);
        } else {
            $('img', this.$container).attr('src', this.part.image.uri);
        }
        if ($('img', this.$container).complete) {
            this.segmenter.load(part);
        }
        $('img', this.$container).on('load', $.proxy(function(event) {
           this.segmenter.load(part);
        }, this));
    }
    
    reset() {
        super.reset();
        if (this.opened) {
            this.segmenter.reset();
        }
    }
}
