/*
Baseline editor
a javascript based baseline segmentation editor,
requires paper.js and colorThief is optional.

Usage:
var segmenter = new Segmenter(img, options);
segmenter.load([{baseline: [[0,0],[10,10]], mask: null}]);

Options:
  lengthTreshold=15
  lengthTreshold=15,
  delayInit=false,
  deletePointBtn=null,
  deleteSelectionBtn=null,
  toggleMasksBtn=null,
  splitBtn=null,
  mergeBtn=null,

*/
var lastId = 0;
function generateUniqueId() { return lastId++; };

function polyEq(poly1, poly2) {
    // compares polygons point by point
    let noPoly = (poly1 == null && poly2 == null);  // note: null is a singleton.. so we have to compare them separatly
    let samePoly = (poly1 && poly2 &&
                    poly1.length != undefined && poly1.length === poly2.length &&
                    poly1.every((pt, index) => pt[0] === poly2[index][0] && pt[1] === poly2[index][1]));
    return (noPoly || samePoly);
}

function isRightClick(event) {
    return event.which === 3 || event.button === 2;
}

class SegmenterRegion {
    constructor(polygon, context, segmenter_) {
        this.id = generateUniqueId();
        this.segmenter = segmenter_;
        this.polygon = polygon;
        this.context = context;
        this.selected = false;
        this.polygonPath = new Path({
            closed: true,
            opacity: 0.4,
            strokeColor: this.segmenter.regionColor,
            dashOffset: 5/this.segmenter.scale,
            strokeWidth: 2/this.segmenter.scale,
            // fillColor: this.segmenter.regionColor,
            selectedColor: this.segmenter.selectedColor,
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
        let previous = {polygon: this.polygon};
        this.polygonPath.reduce();  // removes unecessary segments
        this.polygon = this.polygonPath.segments.map(s => [Math.round(s.point.x),
                                                           Math.round(s.point.y)]);
        if (!polyEq(previous.polygon, this.polygon)) {
            this.segmenter.trigger('baseline-editor:update', {objType: 'region',
                                                              obj: this,
                                                              previous:previous});
        }
    }
    
    remove() {
        this.polygonPath.remove();
    }
    
    delete() {
        this.unselect();
        this.remove();
        this.segmenter.trigger('baseline-editor:delete', {objType: 'region', obj: this});
    }
}

class SegmenterLine {
    constructor(order, baseline, mask, region, textDirection, context, segmenter_) {
        this.id = generateUniqueId();
        this.order = order;
        this.segmenter = segmenter_;
        this.mask = mask;
        this.region = region;
        this.context = context;
        this.selected = false;
        this.textDirection = textDirection;
        this.directionHint = null;

        if (baseline) {
            if(baseline.segments) {  // already a paperjs.Path
                this.baselinePath = baseline;
            } else {
                let color = this.order%2 ? this.segmenter.evenBaselinesColor : this.segmenter.oddBaselinesColor;
                this.baseline = baseline.map(pt=>[Math.round(pt[0]), Math.round(pt[1])]);
                this.baselinePath = new Path({
                    strokeColor: color,
                    strokeWidth: Math.max(3, 7/this.segmenter.scale),
                    strokeCap: 'butt',
                    selectedColor: 'black',
                    opacity: 0.5,
                    segments: this.baseline,
                    selected: false,
                    visible: true
                });
            }
        } else {
            // No baseline !
            this.baseline = null;
        }

        if (this.mask) {
            this.makeMaskPath();
        } else {
            this.maskPath = null;
        }
        
        this.refresh();
    }
    
    refresh() {
        this.showOrdering();
        this.showDirection();
    }
    
    makeMaskPath() {
        this.maskPath = new Path({
            closed: true,
            opacity: 0.1,
            // Note: not a bug to use baseline color for even masks
            fillColor: this.order % 2 ? this.segmenter.evenBaselinesColor: this.segmenter.oddMasksColor,
            selectedColor: this.segmenter.selectedColor,
            visible: (this.baseline && this.baseline.length==0) || this.segmenter.showMasks,
            segments: this.mask
        });
        // too resource intensive :(
        // if (this.mask.length > this.segmenter.maxSegments) this.maskPath.simplify();
    }
    
    select() {
        if (this.selected) return;
        if (this.maskPath && this.maskPath.visible) {
            this.maskPath.selected = true;
            this.maskPath.bringToFront();
        }
        if (this.baselinePath) {
            this.baselinePath.selected = true;
            this.baselinePath.bringToFront();
            this.baselinePath.strokeColor = this.segmenter.selectedColor;
        }
        this.segmenter.addToSelection(this);
        this.selected = true;
        if (this.orderDisplay) this.orderDisplay.bringToFront();
    }

    unselect() {
        if (!this.selected) return;
        // also unselects any selected segments
        if (this.maskPath) {
            this.maskPath.selected = false;
            for (let i=0; i<this.maskPath.segments.length; i++) {
                if (this.maskPath.segments[i].point.selected) {
                    this.segmenter.removeFromSelection(this.maskPath.segments[i]);
                }
            }
        }
        if (this.baselinePath) {
            this.baselinePath.selected = false;
            this.baselinePath.strokeColor = this.order%2 ? this.segmenter.evenBaselinesColor : this.segmenter.oddBaselinesColor;
            for (let i=0; i<this.baselinePath.segments; i++) {
                this.segmenter.removeFromSelection(this.baselinePath.segments[i]); 
            }
        }
        this.segmenter.removeFromSelection(this);
        this.selected = false;
    }
    
    toggleSelect() {
        if (this.selected) this.unselect();
        else this.select();
    }
    
    update(baseline, mask) {
        if (baseline && baseline.length) {
            this.baseline = baseline;
            this.baselinePath.removeSegments();
            this.baselinePath.addSegments(baseline);
            this.segmenter.bindLineEvents(this);
        }
        if (mask && mask.length) {
            if (! this.maskPath) {
                this.makeMaskPath();
            }
            this.mask = mask;
            this.maskPath.removeSegments();
            this.maskPath.addSegments(mask);
            this.segmenter.bindMaskEvents(this);
        }
    }
    
    updateDataFromCanvas() {
        let previous = {baseline: this.baseline, mask: this.mask};
        if (this.baselinePath) {
            this.baselinePath.reduce();  // removes unecessary segments
            this.baseline = this.baselinePath.segments.map(s => [Math.round(s.point.x), Math.round(s.point.y)]);
        }
        if (this.maskPath) {
            this.maskPath.reduce();
            this.mask = this.maskPath.segments.map(s => [Math.round(s.point.x), Math.round(s.point.y)]);
        }
        if (!polyEq(previous.baseline, this.baseline) || !polyEq(previous.mask, this.mask)) {
            this.segmenter.trigger('baseline-editor:update', {objType: 'line',
                                                              obj: this,
                                                              previous:previous});
        }
    }
    
    extend(point) {
        return this.baselinePath.add(point);
    }
    
    remove() {
        this.unselect();
        if(this.baselinePath) this.baselinePath.remove();
        if(this.maskPath) this.maskPath.remove();
        if(this.directionHint) this.directionHint.remove();
        if(this.orderDisplay) this.orderDisplay.remove();
        this.segmenter.lines.splice(this.segmenter.lines.findIndex(e => e.id == this.id), 1);
    }
    
    delete() {
        this.unselect();
        this.remove();
        this.segmenter.trigger('baseline-editor:delete', {objType: 'line', obj: this});
    }

    reverse() {
        if (this.baselinePath) {
            let previous = {baseline: this.baseline, mask: this.mask};
            this.baselinePath.reverse();
            this.refresh();
            this.updateDataFromCanvas();
        }
    }

    showOrdering() {
        let anchorPath = this.baselinePath?this.baselinePath:this.maskPath;
        let anchor = (this.textDirection == 'lr' ?
                      anchorPath.firstSegment.point :
                      anchorPath.lastSegment.point);
        let offset = 10, circle, text;
        if (!this.orderDisplay) {
            this.segmenter.orderingLayer.activate();
            circle = new Shape.Circle(anchor, offset);
            circle.fillColor = 'yellow';
            circle.strokeColor = 'black';
            text = new PointText(anchor);
            text.fillColor = 'black';
            text.fontSize = offset;
            text.fontWeight = 'bold';
            text.justification = 'center';
            text.content = parseInt(this.order)+1;
            this.orderDisplay = new Group({
                children: [circle, text]
            });
            this.orderDisplay.scale(1/this.segmenter.scale);
            // for some reason we need to reposition it after scaling
            text.position = anchor;
        } else {
            let circle = this.orderDisplay.children[0], text = this.orderDisplay.children[1];
            circle.position = anchor;
            text.position = anchor;
        }
    }

    showDirection() {
        // shows an orthogonal segment at the start of the line, length depends on line height
        if (this.baselinePath && this.baselinePath.segments.length > 1) {
            this.segmenter.linesLayer.activate();
            if (this.directionHint === null) {
                this.directionHint = new Path({
                    visible: true,
                    strokeWidth: Math.max(2, 4 / this.segmenter.scale),
                    opacity: 0.5,
                    strokeColor: this.segmenter.directionHintColor
                });
                this.segmenter.dirHintsGroup.addChild(this.directionHint);
            }
            let anchor;
            if (this.textDirection == 'lr') {
                anchor = this.baselinePath.firstSegment;
            } else {
                anchor = this.baselinePath.lastSegment;
            }
            let vector = this.baselinePath.getNormalAt(this.baselinePath.getOffsetOf(anchor.point));
            if (vector) {
                vector.length = this.getLineHeight()/2;
                this.directionHint.sendToBack();
                this.directionHint.segments = [anchor.point.subtract(vector),
                                               anchor.point.add(vector)];
            }
        }
    }
    
    getLineHeight() {
        if (this.maskPath) {
            // area implementation
            if (this.baselinePath) {
                return Math.round(Math.abs(this.maskPath.area) / this.baselinePath.length);
            } else {
                return this.maskPath.bounds.height;  // weird results for skewed lines
            }
        } else {
            return this.segmenter.getAverageLineHeight();
        }
    }
}

class Segmenter {
    constructor(image, {lengthTreshold=10,
                        // scale = real coordinates to image coordinates
                        // for example if drawing on a 1000px wide thumbnail for a 'real' 3000px wide image,
                        // the scale would be 1/3, the container (DOM) width is irrelevant here.
                        scale=1,
                        delayInit=false,
                        // deletePointBtn=null,
                        // deleteSelectionBtn=null,
                        // toggleMasksBtn=null,
                        // toggleRegionModeBtn=null,
                        // toggleOrderingBtn=null,
                        // splitBtn=null,
                        // mergeBtn=null,
                        // reverseBtn=null,
                        disableBindings=false,

                        evenBaselinesColor=null,
                        oddBaselinesColor=null,
                        oddMasksColor=null,
                        directionHintColor=null,
                        regionColor=null,
                        
                        inactiveLayerOpacity=0.5,
                        maxSegments=50,
                        // when creating a line, which direction should it take.
                        defaultTextDirection='lr',
                        // field to store and reuse in output from loaded data
                        // can be set to null to disable behavior
                        idField='id'
                       } = {}) {
        this.img = image;
        this.mode = 'lines'; // | 'regions'
        this.lines = [];
        this.regions = [];
        this.selection = {lines:[], segments:[], regions:[]};
        this.defaultTextDirection = defaultTextDirection;
        
        this.scale = scale;
        this.canvas = document.createElement('canvas');
        this.canvas.style.position = 'absolute';
        this.canvas.style.top = 0;
        this.canvas.style.left = 0;
        this.canvas.style.width = this.img.width;
        this.canvas.style.height = this.img.height;

        // paper.js helpers
        this.inactiveLayerOpacity = inactiveLayerOpacity;
        this.linesLayer = this.regionsLayer = this.orderingLayer = null;
        this.regionsGroup = null;
        
        this.idField = idField;
        this.disableBindings = disableBindings;
        
        // create a dummy tag for event bindings
        this.events = document.createElement('div');
        this.events.setAttribute('id', 'baseline-editor-events');
        document.body.appendChild(this.events);
        
        // this.raster = null;
        // insert after..
        this.img.parentNode.insertBefore(this.canvas, this.img);
        
        this.evenBaselinesColor=evenBaselinesColor;
        this.oddBaselinesColor=oddBaselinesColor;
        this.oddMasksColor=oddMasksColor;
        this.directionHintColor=directionHintColor;
        this.regionColor=regionColor;
        this.maxSegments = maxSegments;
        
        // the minimal length in pixels below which the line will be removed automatically
        this.lengthThreshold = lengthTreshold; 
        this.showMasks = false;
        this.showLineNumbers = false;
        
        this.selecting = null;
        this.spliting = false;
        this.copy = null;

        // menu btns
        this.toggleMasksBtn = document.getElementById('be-toggle-masks');
        this.toggleOrderingBtn = document.getElementById('be-toggle-order');
        this.toggleRegionModeBtn = document.getElementById('be-toggle-regions');
        
        // contextual btns
        this.deletePointBtn = document.getElementById('be-delete-point');
        // this.deletePointBtn.style.zIndex = 3;
        this.splitBtn = document.getElementById('be-split-lines');
        this.deleteSelectionBtn = document.getElementById('be-delete-selection');
        this.mergeBtn = document.getElementById('be-merge-selection');
        this.reverseBtn = document.getElementById('be-reverse-selection');
        this.linkRegionBtn = document.getElementById('be-link-region');
        this.unlinkRegionBtn = document.getElementById('be-unlink-region');
        
        // editor settings
        this.evenBaselinesColorInput = document.getElementById('be-even-bl-color');
        this.oddBaselinesColorInput = document.getElementById('be-odd-bl-color');
        this.oddMaskColorInput = document.getElementById('be-odd-mask-color');
        this.dirHintColorInput = document.getElementById('be-dir-color');
        this.regionColorInput = document.getElementById('be-reg-color');
        
        // create a menu for the context buttons
        this.contextMenu = document.createElement('div');
        this.contextMenu.id = 'context-menu';
        this.contextMenu.style.position = 'fixed';
        this.contextMenu.style.display = 'none';
        this.contextMenu.style.zIndex = 3;
        this.contextMenu.style.border = '1px solid grey';
        this.contextMenu.style.borderRadius = '5px';
        this.deleteSelectionBtn.parentNode.insertBefore(this.contextMenu, this.deleteSelectionBtn);
        if (this.linkRegionBtn) this.contextMenu.appendChild(this.linkRegionBtn);
        if (this.unlinkRegionBtn) this.contextMenu.appendChild(this.unlinkRegionBtn);
        if (this.mergeBtn) this.contextMenu.appendChild(this.mergeBtn);
        if (this.reverseBtn) this.contextMenu.appendChild(this.reverseBtn);
        if (this.deletePointBtn) this.contextMenu.appendChild(this.deletePointBtn);
        if (this.deleteSelectionBtn) this.contextMenu.appendChild(this.deleteSelectionBtn);
        
        this.bindButtons();
        
        // init paperjs
        if (!delayInit) {
            this.init();
        }
    }

    reset() {
        this.empty();
    }
    
    deleteSelection() {
        // FIXME: use the bulk_delete endpoints when it's merged.
        for (let i=this.selection.lines.length-1; i >= 0; i--) {    
            this.selection.lines[i].delete();
        }
        for (let i=this.selection.regions.length-1; i>=0; i--) {
            this.selection.regions[i].delete();
        }
        this.showContextMenu();
    }
    deleteSelectedSegments() {
        for (let i=this.selection.segments.length-1; i >= 0; i--) {
            let segment = this.selection.segments[i];
            if (segment.path && (
                (segment.path.closed && segment.path.segments.length > 3) ||
                    segment.path.segments.length > 2)) {
                this.selection.segments[i].remove();
                this.selection.segments.pop();
            }
        }
        
        // using the fact that selecting a segment also selects its line
        for (let i=0; i < this.selection.lines.length; i++) {    
            this.selection.lines[i].updateDataFromCanvas();
        }
        this.showContextMenu();
    }
    
    bindButtons() {
        this.deleteSelectionBtn.addEventListener('click', function(event) {
            this.deleteSelection();
        }.bind(this));

        this.deletePointBtn.addEventListener('click', function() {
            this.deleteSelectedSegments();
        }.bind(this));

        if (this.toggleRegionModeBtn) this.toggleRegionModeBtn.addEventListener('click', function(event) {
            this.toggleRegionMode();
        }.bind(this));
        
        if (this.toggleMasksBtn) {
            this.toggleMasksBtn.addEventListener('click', function(event) {
                this.toggleMasks();
            }.bind(this));
        }

        if (this.splitBtn) this.splitBtn.addEventListener('click', function(event) {
            this.spliting = !this.spliting;
            this.splitBtn.classList.toggle('btn-warning');
            this.splitBtn.classList.toggle('btn-success');
            this.setCursor();
        }.bind(this));
        if (this.mergeBtn) this.mergeBtn.addEventListener('click', function(event) {
            this.mergeSelection();
        }.bind(this));
        if (this.linkRegionBtn) this.linkRegionBtn.addEventListener('click', function(event) {
            this.linkSelection();
        }.bind(this));
        if (this.unlinkRegionBtn) this.unlinkRegionBtn.addEventListener('click', function(event) {
            this.unlinkSelection();
        }.bind(this));
        if (this.reverseBtn) this.reverseBtn.addEventListener('click', function(event) {
            this.reverseSelection();
        }.bind(this));

        if (this.toggleOrderingBtn) this.toggleOrderingBtn.addEventListener('click', function(ev) {
            this.toggleOrdering();
        }.bind(this));

        // colors
        this.evenBaselinesColorInput.addEventListener('change', function(ev) {
            this.evenBaselinesColor = ev.target.value;
            this.evenLinesGroup.strokeColor = ev.target.value;
            this.evenMasksGroup.strokeColor = ev.target.value;
            this.evenMasksGroup.fillColor = ev.target.value;
        }.bind(this));
        this.oddBaselinesColorInput.addEventListener('change', function(ev) {
            this.oddBaselinesColor = ev.target.value;
            this.oddLinesGroup.strokeColor = ev.target.value;
        }.bind(this));
        this.oddMaskColorInput.addEventListener('change', function(ev) {
            this.oddMasksColor = ev.target.value;
            this.oddMasksGroup.strokeColor = ev.target.value;
            this.oddMasksGroup.fillColor = ev.target.value;
        }.bind(this));
        this.dirHintColorInput.addEventListener('change', function(ev) {
            this.directionHintColor = ev.target.value;
            this.dirHintsGroup.strokeColor = ev.target.value;
        }.bind(this));
        this.regionColorInput.addEventListener('change', function(ev) {
            this.regionColor = ev.target.value;
            this.regionsGroup.strokeColor = ev.target.value;
            if (this.mode == 'regions') this.regionsGroup.fillColor = ev.target.value;
        }.bind(this));
        
        document.addEventListener('keydown', function(event) {
            if (this.disableBindings) return;
            if (event.keyCode == 27) { // escape
                this.purgeSelection();
            } else if (event.keyCode == 46) { // supr
                if (event.ctrlKey) {
                    this.deleteSelectedSegments();
                } else {
                    this.deleteSelection();
                }
            } else if (event.keyCode == 67) { // C
                this.spliting = !this.spliting;
                this.splitBtn.classList.toggle('btn-warning');
                this.splitBtn.classList.toggle('btn-success');
                this.setCursor();
            } else if (event.keyCode == 77) { // M
                this.toggleMasks();
            } else if (event.keyCode == 82) { // R
                this.toggleRegionMode();
            } else if (event.keyCode == 65 && event.ctrlKey) { // Ctrl+A
                event.preventDefault();
                event.stopPropagation();
                // select all
                if (this.mode == 'lines') {
                    for (let i in this.lines) this.lines[i].select();
                } else if (this.mode == 'regions') {
                    for (let i in this.regions) this.regions[i].select();
                }
            }

            // Attempt to duplicate content...
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
        
        document.addEventListener('mousedown', function(event) {
            if (event.target != this.canvas && !this.contextMenu.contains(event.target)) {
                this.purgeSelection();
            }
        }.bind(this));
    }
    
    init() {
        paper.settings.handleSize = 10;
        paper.settings.hitTolerance = 0;  // Note: doesn't work?
        paper.install(window);
        paper.setup(this.canvas);
        
        this.regionsGroup = new paper.Group();
        this.evenLinesGroup = new paper.Group();
        this.oddLinesGroup = new paper.Group();
        this.evenMasksGroup = new paper.Group();
        this.oddMasksGroup = new paper.Group();
        this.dirHintsGroup = new paper.Group();
        
        this.linesLayer = paper.project.activeLayer;
        this.regionsLayer = new paper.Layer();
        this.orderingLayer = new paper.Layer();
        this.orderingLayer.visible = this.showLineNumbers;
        if (this.mode == 'lines') {
            this.evenLinesGroup.bringToFront();
            this.oddLinesGroup.bringToFront();
            this.regionsLayer.opacity = this.inactiveLayerOpacity;
        } else if (this.mode == 'regions') {
            this.regionsGroup.bringToFront();
            this.linesLayer.opacity = this.inactiveLayerOpacity;
        }
        if (this.showLineNumbers) {
            this.orderingLayer.bringToFront();
        }
        
        this.refresh();
        
        // make sure we capture clicks before the img
        this.canvas.style.zIndex = this.img.style.zIndex + 1;
        
        var tool = new Tool();
        this.setColors(this.img);
        this.setCursor();

        // this.raster = new Raster(this.img);  // Note: this seems to slow down everything significantly
        // this.raster.position = view.center;
        // this.img.style.display = 'hidden';
        
        // context follows top right, width can only be calculated once shown
        this.contextMenu.style.top = (this.img.getBoundingClientRect().top+10)+'px';
        this.contextMenu.style.margin = '10px';
        
        tool.onMouseDown = this.onMouseDown.bind(this);
        
        this.tool = tool;
        this.tool.activate();
        return tool;
    }
    
    createLine(order, baseline, mask, region, context, postponeEvents) {
        if (this.idField) {
            if (context === undefined || context === null) {
                context = {};
            }
            if (context[this.idField] === undefined) {
                // make sure the client receives a value for its id, even if it's null for a new line
                context[this.idField] = null;
            }
        }
        
        if (!order) order = parseInt(this.getMaxOrder()) + 1;
        this.linesLayer.activate();
        var line = new SegmenterLine(order, baseline, mask, region,
                                     this.defaultTextDirection, context, this);
        
        if (line.order%2) {
            this.evenLinesGroup.addChild(line.baselinePath);
            if (line.maskPath) this.evenMasksGroup.addChild(line.maskPath);
        } else {
            this.oddLinesGroup.addChild(line.baselinePath);
            if (line.maskPath) this.oddMasksGroup.addChild(line.maskPath);
        }
        
        if (!postponeEvents) {
            this.bindLineEvents(line);
            this.bindMaskEvents(line);
        }
        this.lines.push(line);
        return line;
    }
    
    finishLine(line) {
        if (line.baselinePath.length < this.lengthThreshold) {
            line.remove();
        } else {
            this.bindLineEvents(line);
            line.updateDataFromCanvas();
        }
        this.resetToolEvents();  // unregistering
    }

    createRegion(polygon, context, postponeEvents) {
        if (this.idField) {
            if (context === undefined || context === null) {
                context = {};
            }
            if (context[this.idField] === undefined) {
                // make sure the client receives a value for its id, even if it's null for a new region
                context[this.idField] = null;
            }
        }
        this.regionsLayer.activate();
        var region = new SegmenterRegion(polygon, context, this);
        if (!postponeEvents) this.bindRegionEvents(region);
        this.regions.push(region);
        this.regionsGroup.addChild(region.polygonPath);
        return region;
    }

    finishRegion(region) {
        this.bindRegionEvents(region);
        this.resetToolEvents();
        region.updateDataFromCanvas();
    }

    bindRegionEvents(region) {
        region.polygonPath.onMouseDown = function(event) {
            if (event.event.ctrlKey ||
                this.selecting ||
                isRightClick(event.event) ||
                this.mode != 'regions') return;
            this.selecting = region;
            
            var dragging = region.polygonPath.getNearestLocation(event.point).segment;
            this.tool.onMouseDrag = function(event) {
                this.selecting = false;
                if (!event.event.shiftKey) {
                    this.movePointInView(dragging.point, event.delta);
                }
            }.bind(this);

            var hit = region.polygonPath.hitTest(event.point, {
	            segments: true,
	            tolerance: 20
            });
            if (hit && hit.type=='segment') {
                if (this.selection.segments.findIndex(
                    e => e.path.id == hit.segment.path.id && e.index == hit.segment.index) == -1) {
                    this.addToSelection(hit.segment);
                } else {
                    this.removeFromSelection(hit.segment);
                }
            }
            this.tool.onMouseUp = function(event) {
                this.resetToolEvents();
                this.updateRegionsFromCanvas();
            }.bind(this);
        }.bind(this);

        region.polygonPath.onDoubleClick = function(event) {
            // Creates a new control point in the region
            if (event.event.ctrlKey || this.mode != 'regions') return;
            let location = region.polygonPath.getNearestLocation(event.point);
            let newSegment = region.polygonPath.insert(location.index+1, location);
        }.bind(this);
    }
    
    bindLineEvents(line) {
        if (line.baselinePath) {
            line.baselinePath.onMouseDown = function(event) {
                if (event.event.ctrlKey ||
                    isRightClick(event.event) ||
                    this.mode != 'lines' ||
                    this.selecting) return;
                this.selecting = line;
                var hit = line.baselinePath.hitTest(event.point, {
	                segments: true,
	                tolerance: 20
                });
                
                if (hit && hit.type=='segment') {
                    if (this.selection.segments.findIndex(
                        e => e.path && e.path.id == hit.segment.path.id && e.index == hit.segment.index) == -1) {
                        this.addToSelection(hit.segment);
                    } else {
                        this.removeFromSelection(hit.segment);
                    }
                }
                var dragging = line.baselinePath.getNearestLocation(event.point).segment;
                this.tool.onMouseDrag = function(event) {
                    if (!event.event.shiftKey) {
                        this.movePointInView(dragging.point, event.delta);
                        this.setCursor('move');
                        line.refresh();
                    }
                }.bind(this);
                
                this.tool.onMouseUp = function(event) {
                    this.resetToolEvents();
                    line.updateDataFromCanvas();
                }.bind(this);
            }.bind(this);

            line.baselinePath.onDoubleClick = function(event) {
                if (event.event.ctrlKey || this.mode != 'lines') return;
                let location = line.baselinePath.getNearestLocation(event.point);
                let newSegment = line.baselinePath.insert(location.index+1, location);
                // line.baselinePath.smooth({ type: 'catmull-rom', 'factor': 0.2 });
            }.bind(this);
            
            line.baselinePath.onMouseMove = function(event) {
                if (event.event.ctrlKey || this.mode != 'lines') return;
                if (line.selected) this.setCursor('grab');
                else this.setCursor('pointer');
                var hit = line.baselinePath.hitTest(event.point, {
	                segments: true,
	                tolerance: 5
                });
                if (hit && hit.type=='segment') {
                    this.setCursor('pointer');
                }
            }.bind(this);
            
            line.baselinePath.onMouseLeave = function(event) {
                this.setCursor();
            }.bind(this);
            
            // line.baselinePath.onMouseDrag = function(event) {
            //     if (event.event.ctrlKey || this.mode != 'lines') return;
            //     this.setCursor('move');
            // }.bind(this);
        }
    }
    
    bindMaskEvents(line) {   
        // same for the masks
        if (line.maskPath) {
            line.maskPath.onMouseDown = function(event) {
                if (event.event.ctrlKey ||
                    isRightClick(event.event) ||
                    this.selecting ||
                    this.mode != 'lines') return;
                this.selecting = line;

                var hit = line.maskPath.hitTest(event.point, {
	                segments: true,
	                tolerance: 20
                });
                if (hit && hit.type=='segment') {
                    if (this.selection.segments.findIndex(
                        e => e.path && e.path.id == hit.segment.path.id && e.index == hit.segment.index) == -1) {
                        this.addToSelection(hit.segment);
                    } else {
                        this.removeFromSelection(hit.segment);
                    }
                }
                var dragging = line.maskPath.getNearestLocation(event.point).segment;
                this.tool.onMouseDrag = function(event) {
                    this.selecting = false;
                    if (!event.event.shiftKey && !event.event.ctrlKey) {
                        this.movePointInView(dragging.point, event.delta);
                    }
                }.bind(this);
                
                this.tool.onMouseUp = function(event) {
                    this.resetToolEvents();
                    line.updateDataFromCanvas();
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
    }
    
    resetToolEvents() {
        this.tool.onMouseDown = this.onMouseDown.bind(this);
        this.tool.onMouseDrag = this.onMouseDrag.bind(this);
        this.tool.onMouseMove = null;
        this.tool.onMouseUp = null;
    }

    multiMove(event) {
        var delta = event.delta;
        if (this.mode == 'lines') {
            if (this.selection.segments.length) {
                for (let i in this.selection.segments) {
                    this.movePointInView(this.selection.segments[i].point, delta);
                    this.movePointInView(this.selection.segments[i].point, delta);
                }
                for (let i in this.selection.lines) {
                    this.selection.lines[i].refresh();
                }
            } else {
                for (let i in this.selection.lines) {
                    let l = this.selection.lines[i];
                    if(l.baselinePath) this.movePointInView(l.baselinePath.position, delta);
                    if(l.maskPath) this.movePointInView(l.maskPath.position, delta);
                    l.refresh();
                }
            }
        } else if (this.mode == 'regions') {
            for (let i in this.selection.regions) {
                this.movePointInView(this.selection.regions[i].polygonPath.position, delta);
            }
        }
    }
    
    onMouseDrag(event) {
        if (event.event.ctrlKey) {
            this.multiMove(event);
            this.tool.onMouseUp = function(event) {
                this.resetToolEvents();
                if (this.mode == 'lines') {
                    for (let i in this.selection.lines) {
                        this.selection.lines[i].updateDataFromCanvas();
                    }
                } else if (this.mode == 'regions') {
                    for (let i in this.selection.regions) {
                        this.selection.regions[i].updateDataFromCanvas();
                    }
                }
            }.bind(this);
        }
    }
    
    onMouseDown(event) {
        if (isRightClick(event.event)) return;
        if (this.selecting) {
            // selection
            if (event.event.shiftKey) {
                this.selecting.toggleSelect();
                this.startLassoSelection(event);
            } else {
                this.selecting.select();
                this.purgeSelection(this.selecting);
            }
            this.trigger('baseline-editor:selection', {target: this.selecting, selection: this.selection});
            this.selecting = null;
        } else {
            if (event.event.ctrlKey) return;
            if (this.spliting) {
                this.startCuter(event);
            } else if (event.event.shiftKey) {
                // lasso selection tool
                this.startLassoSelection(event);
            } else if (this.hasSelection()) {
                this.purgeSelection();
            } else if (this.mode == 'regions') {
                this.startNewRegion(event);
            }  else {  // mode = 'lines'
                // create a new line
                this.startNewLine(event);
            }
        }
    }

    getRegionsAt(pt) {
        // returns all the regions that contains the given point pt
        return this.regions.filter(r => r.polygonPath.contains(pt));
    }
    
    startNewLine(event) {
        this.purgeSelection();

        let clickLocation = [event.point.x, event.point.y];
        // check if we start from a known region, if we do we bind the line to it.
        let region = this.getRegionsAt(clickLocation).pop() || null;
        let newLine = this.createLine(null, [clickLocation], null, region, null, true);
        let point = newLine.extend(event.point).point;  // the point that we move around

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
                newLine.unselect();
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
        document.addEventListener('keyup', onCancel, {once: true});
    }
    
    startNewRegion(event) {
        this.purgeSelection();
        var originPoint = event.point;
        let newRegion = this.createRegion([
            [event.point.x, event.point.y],
            [event.point.x, event.point.y+1],
            [event.point.x+1, event.point.y+1],
            [event.point.x+1, event.point.y]
        ], null);
        newRegion.polygonPath.fillColor = this.regionColor;
        
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
        document.addEventListener('keyup', onCancel, {once: true});
    }
    
    startCuter(event) {
        // rectangle cutter
        let clip = this.makeSelectionRectangle(event);
        let onCancel = function(event) {
            if (event.keyCode == 27) {  // escape
                clip.remove();
                this.resetToolEvents();
                document.removeEventListener('mouseup', finishCut);
                document.removeEventListener('keyup', onCancel);
                return false;
            }
            return null;
        }.bind(this);
        let finishCut = function(event) {
            this.splitByPath(clip);
            clip.remove();
            
            this.resetToolEvents();
            document.removeEventListener('mouseUp', finishCut);
            document.removeEventListener('keyup', onCancel);
        }.bind(this);
        
        this.tool.onMouseDrag = function(event) {
            this.updateSelectionRectangle(clip, event);
            this.splitHelper(clip, event);
        }.bind(this);
        document.addEventListener('mouseup', finishCut, {once: true});
        document.addEventListener('keyup', onCancel, {once: true});
    }
    
    startLassoSelection(event) {
        let clip = this.makeSelectionRectangle(event);
        let onCancel = function(event) {
            if (event.keyCode == 27) {  // escape
                clip.remove();
                this.purgeSelection();
                this.resetToolEvents();
                document.removeEventListener('mouseup', finishSelection);
                document.removeEventListener('keyup', onCancel);
                return false;
            }
            return null;
        }.bind(this);
        let finishSelection = function(event) {
            clip.remove();
            this.resetToolEvents();
            document.removeEventListener('mouseup', finishSelection);
            document.removeEventListener('keyup', onCancel);
            this.trigger('baseline-editor:selection', {target: this.selecting, selection: this.selection});
        }.bind(this);

        let allLines = this.selection.lines.length && this.selection.lines || this.lines;
        let allRegions = this.selection.regions.length && this.selection.regions || this.regions;
        let tmpSelected = [];
        this.tool.onMouseDrag = function(event) {
            this.updateSelectionRectangle(clip, event);
            if (this.mode == 'lines') {
                this.lassoSelectionLines(clip, allLines, tmpSelected);
            }  else if (this.mode == 'regions') {
                this.lassoSelectionRegions(clip, allRegions, tmpSelected);
            }
        }.bind(this);

        document.addEventListener('mouseup', finishSelection);
        document.addEventListener('keyup', onCancel);
    }
    
    movePointInView(point, delta) {
        point.x += delta.x;
        point.y += delta.y;
        if (point.x < 0) point.x = 0;
        if (point.x > this.img.naturalWidth/this.scale) point.x = this.img.naturalWidth/this.scale;
        if (point.y < 0) point.y = 0;
        if (point.y > this.img.naturalHeight/this.scale) point.y = this.img.naturalHeight/this.scale;
    }
    
    empty() {
        for (let i=this.lines.length-1; i>=0; i--) { this.lines[i].remove(); }
        this.lines = [];
        for (let i=this.regions.length-1; i>=0; i--) { this.regions[i].remove(); }
        this.regions = [];
    }
    
    refresh() {
        /*
          Call when either the available space or the source image size changed.
        */
        if (paper.view) {
            let bounds = this.img.getBoundingClientRect();
            let imgRatio = (bounds.width / this.img.naturalWidth);
            let ratio = imgRatio/paper.view.zoom*this.scale;
            this.canvas.style.width = bounds.width + 'px';
            this.canvas.style.height = bounds.height + 'px';
            if (paper.view.viewSize[0] != bounds.width &&
                paper.view.viewSize[1] != bounds.height) {
                paper.view.viewSize = [bounds.width, bounds.height];
                paper.view.scale(ratio, [0, 0]);
            }
        }
    }
    
    load(data) {
        /* Loads a list of lines containing each a baseline polygon and a mask polygon
         * [{baseline: [[x1, y1], [x2, y2], ..], mask:[[x1, y1], [x2, y2], ]}, {..}] */
        for (let i in data.lines) {
            let line = data.lines[i];
            let context = {};
            if ((line.baseline !== null && line.baseline.length) ||
                (line.mask !== null && line.mask.length)) {
                if (this.idField) context[this.idField] = line[this.idField];
                if (!line.baseline) this.toggleMasks(true);
                this.createLine(i, line.baseline, line.mask, line.block, context);
            } else {
                console.log('EDITOR SKIPING invalid line: ', line);
            }
        }
        
        for (let i in data.regions) {
            let region = data.regions[i];
            let context = {};
            if (this.idField) context[this.idField] = region[this.idField];
            this.createRegion(region.box, context);
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
            regions: this.regions.map(region => region.polygon),
            lines: this.lines.map(function(line) {
                return {
                    baseline: line.baseline,
                    mask: line.mask
                };
            }.bind(this))
        };
    }

    trigger(eventName, data) {
        var event = new CustomEvent(eventName, {detail:data});
        this.events.dispatchEvent(event);
    }
    
    updateLinesFromCanvas() {
        for (let i in this.lines) {
            this.lines[i].updateDataFromCanvas();
        }
    }
    
    updateRegionsFromCanvas() {
        for (let i in this.regions) {
            this.regions[i].updateDataFromCanvas();
        }
    }
    
    toggleMasks(force) {
        this.showMasks = force || !this.showMasks;
        if (this.showMasks) {
            this.toggleMasksBtn.classList.add('btn-success');
            this.toggleMasksBtn.classList.remove('btn-info');
        } else {
            this.toggleMasksBtn.classList.add('btn-info');
            this.toggleMasksBtn.classList.remove('btn-success');
        }
        for (let i in this.lines) {
            let poly = this.lines[i].maskPath;
            if (poly) {
                poly.visible = this.showMasks;
                // paperjs shows handles for invisible items :(
                if (!poly.visible && poly.selected) poly.selected = false;
                if (poly.visible && this.lines[i].selected) poly.selected = true;
            }
        }
    }
    
    toggleOrdering() {
        this.showLineNumbers = !this.showLineNumbers;
        this.orderingLayer.visible = this.showLineNumbers;
        if (this.showLineNumbers) {
            this.toggleOrderingBtn.classList.add('btn-success');
            this.toggleOrderingBtn.classList.remove('btn-info');
            this.orderingLayer.bringToFront();
        } else {
            this.toggleOrderingBtn.classList.add('btn-info');
            this.toggleOrderingBtn.classList.remove('btn-success');
        }
    }
    
    toggleRegionMode() {
        this.purgeSelection();
        if (this.mode == 'lines') {
            this.mode = 'regions';
            this.regionsGroup.fillColor = this.regionColor;
            this.regionsGroup.bringToFront();
            this.regionsLayer.opacity = 1;
            this.linesLayer.opacity = this.inactiveLayerOpacity;
        } else {
            this.mode = 'lines';
            this.regionsGroup.fillColor = null;
            this.regionsGroup.sendToBack();
            // this.evenLinesGroup.bringToFront();
            // this.oddLinesGroup.bringToFront();
            this.regionsLayer.opacity = this.inactiveLayerOpacity;
            this.linesLayer.opacity = 1;
        }
        this.toggleRegionModeBtn.classList.toggle('btn-info');
        this.toggleRegionModeBtn.classList.toggle('btn-success');
    }
    
    showContextMenu() {
        if (!this.hasSelection()) {
            this.contextMenu.style.display = 'none';
            return;
        }

        if (this.linkRegionBtn) this.linkRegionBtn.style.display = 'none';
        if (this.unlinkRegionBtn) this.unlinkRegionBtn.style.display = 'none';
        if (this.mergeBtn) this.mergeBtn.style.display = 'none';
        if (this.reverseBtn) this.reverseBtn.style.display = 'none';
        if (this.deletePointBtn) this.deletePointBtn.style.display = 'none';
        
        if (this.selection.lines.length) {
            if (this.reverseBtn) this.reverseBtn.style.display = 'block';
            if (this.deleteSelectionBtn) this.deleteSelectionBtn.style.display = 'block';
            // we can only merge if all lines contain a baseline
            if (this.selection.lines.filter(l => l.baseline !== null).length > 1) {
                this.mergeBtn.style.display = 'block';
            }
            if (this.regions.length > 0) {
                if (this.selection.lines.filter(l => l.region == null).length > 0) {
                    this.linkRegionBtn.style.display = 'block';
                }
                if (this.selection.lines.filter(l => l.region !== null).length > 0) {
                    this.unlinkRegionBtn.style.display = 'block';
                }
            }
        }
        
        if (this.selection.segments.length) {
            if (this.deletePointBtn) this.deletePointBtn.style.display = 'block';
        }
        
        if (this.selection.regions.length) {
            if (this.deleteSelectionBtn) this.deleteSelectionBtn.style.display = 'block';
        }
        
        this.contextMenu.style.display = 'block';
    }

    hasSelection() {
        return (this.selection.lines.length > 0 ||
                this.selection.segments.length > 0 ||
                this.selection.regions.length > 0);
    }
    
    addToSelection(obj) {
        if (obj instanceof SegmenterLine) {
            if (this.selection.lines.findIndex(e => e.id == obj.id) == -1) this.selection.lines.push(obj);
        } else if (obj instanceof SegmenterRegion) {
            if (this.selection.regions.findIndex(e => e.id == obj.id) == -1) this.selection.regions.push(obj);
        } else {
            // must be a segment
            if (this.selection.segments.findIndex(
                e => e.path && e.path.id == obj.path.id && e.index == obj.index) == -1) {
                this.selection.segments.push(obj);
                obj.selected = true;
            }
        }
        this.showContextMenu();
    }

    removeFromSelection(obj) {
        if (obj instanceof SegmenterLine) {
            this.selection.lines.splice(this.selection.lines.findIndex(e => e.id == obj.id), 1);
        } else if (obj instanceof SegmenterRegion) {
            this.selection.regions.splice(this.selection.regions.findIndex(e => e.id == obj.id), 1);
        } else {
            // must be a segment
            let fi = this.selection.segments.findIndex(e => e.path && obj.path && e.path.id == obj.path.id && e.index == obj.index);
            if (fi !== -1) {
                this.selection.segments.splice(fi, 1);
                obj.point.selected = false;
            }
        }
        this.showContextMenu();
    }
    
    purgeSelection(except) {
        for (let i=this.selection.lines.length-1; i >= 0; i--) {
            if (!except || except != this.selection.lines[i]) {
                this.selection.lines[i].unselect();
            }
        }
        for (let i=this.selection.regions.length-1; i >= 0; i--) {
            if (!except || except != this.selection.regions[i]) {
                this.selection.regions[i].unselect();
            }
        }
        for (let i=this.selection.segments.length-1; i >= 0; i--) {
            if (this.selection.segments[i].path == null){
                // clean up any remaining references (paperjs bug?)
                this.selection.segments.splice(i);
            } else if (!except || except.baselinePath != this.selection.segments[i].path) {
                this.removeFromSelection(this.selection.segments[i]);
            }
        }
        this.showContextMenu();
    }
    
    makeSelectionRectangle(event) {
        let shape = new Rectangle([event.point.x, event.point.y], [1, 1]);
        var clip = new Path.Rectangle(shape, 0);
        clip.opacity = 1;
        clip.strokeWidth = Math.max(2, 2/this.scale);
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

    clipSelectPoly(clip, segments, tmpSelected) {
        for (let j in segments) {
            let segment = segments[j];
            if (segment.point.isInside(clip.bounds)) {
                this.addToSelection(segment);
                tmpSelected.push(segment);
            } else {
                let fi = tmpSelected.findIndex(s=>s.path && s.path.id == segment.path.id
                                               && s.index==segment.index);
                if (fi !== -1) {
                    tmpSelected.slice(fi);
                    this.removeFromSelection(segment);
                }
            }
        }
    }
    
    lassoSelectionRegions(clip, allRegions, tmpSelected) {
        // draws a rectangle lasso selection tool that selects every segment it crosses
        for (let i in allRegions) {
            let allSegments;
            let region = allRegions[i];
            this.clipSelectPoly(clip, region.polygonPath.segments, tmpSelected);
            if (region.polygonPath.intersects(clip) || region.polygonPath.isInside(clip.bounds)) region.select();
            else if (allRegions.length == this.regions.length) region.unselect();
        }
    }
    
    lassoSelectionLines(clip, allLines, tmpSelected) {
        // draws a rectangle lasso selection tool that selects every segment it crosses
        for (let i in allLines) {
            let allSegments;
            let line = allLines[i];
            if (this.showMasks && line.maskPath) {
                allSegments = line.baselinePath.segments.concat(line.maskPath.segments);
            } else {
                allSegments = line.baselinePath.segments;
            }
            this.clipSelectPoly(clip, allSegments, tmpSelected);
            if (line.baselinePath.intersects(clip) || line.baselinePath.isInside(clip.bounds)) line.select();
            else if (allLines.length == this.lines.length) line.unselect();
        }
    }
    
    splitHelper(clip, event) {
        this.lines.forEach(function(line) {
            if (!line.baselinePath) return;
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

    getMaxOrder() {
        if (!this.lines.length) return -1;
        return this.lines.map(l=>l.order).reduce((a,b)=>Math.max(a, b));
    }
    
    getDeterminant(v1, v2) {
        let matrix = [[v1.x, v2.x], [v1.y, v2.y]];
        return math.det(matrix);
    }
    
    splitByPath(path) {
        this.lines.forEach(function(line) {
            if (line.baseline !== null) {
                let intersections = line.baselinePath.getIntersections(path);
                for (var i = 0; i < intersections.length; i += 2) {
                    if (i+1 >= intersections.length) {  // one intersection remaining
                        // remove everything in the selection rectangle
                        let location = intersections[i];
                        if (line.maskPath) {
                            line.maskPath.reorient(true);
                            let normal = line.baselinePath.getNormalAt(intersections[i].offset);
                            normal.length = line.maskPath.bounds.height;
                            let anchor = intersections[i].point;
                            let p = new Path.Line(anchor.subtract(normal), anchor.add(normal));
                            let inters = line.maskPath.getIntersections(p);
                            if (inters.length > 1) {
                                line.maskPath.splitAt(inters[1]);
                                let trash = line.maskPath.splitAt(inters[0]);
                                trash.remove();
                                line.maskPath.closePath();
                            }
                        }
                        let newSegment = line.baselinePath.insert(location.index+1, location);
                        if (path.contains(line.baselinePath.firstSegment.point)) {
                            line.baselinePath.removeSegments(0, newSegment.index);
                        } else if (path.contains(line.baselinePath.lastSegment.point)) {
                            line.baselinePath.removeSegments(newSegment.index+1);
                        }
                    } else {
                        let newMask = null;
                        // calculate the normals before splitting
                        let normal1 = line.baselinePath.getNormalAt(intersections[i].offset);
                        let normal2 = line.baselinePath.getNormalAt(intersections[i+1].offset);
                        let split = line.baselinePath.splitAt(intersections[i+1]);
                        let trash = line.baselinePath.splitAt(intersections[i]);
                        trash.remove();
                        
                        // projects the intersections into the mask to cut it as well.
                        if (line.maskPath !== null) {
                            normal1.length = normal2.length = line.maskPath.bounds.height;
                            let anchor1 = intersections[i].point;
                            let anchor2 = intersections[i+1].point;
                            let clip = new Path({segments:[
                                anchor1.add(normal1),
                                anchor1.subtract(normal1),
                                anchor2.subtract(normal2),
                                anchor2.add(normal2)]});
                            let ng = line.maskPath.divide(clip, {insert: false});
                            clip.remove();
                            // we are left with 3 polygons,
                            // calculating the determinant of the normals against their center point
                            // to determine on which side they are.
                            if (ng.children) {
                                let a = intersections[i].point, b = intersections[i+1].point;
                                let fp = line.baselinePath.firstSegment.point;
                                let lp = line.baselinePath.lastSegment.point;
                                let fp2 = split.firstSegment.point;
                                let lp2 = split.lastSegment.point;
                                // if we have more than 3 we don't know what to do with them
                                for (let n in ng.children.slice(0, 3)) {
                                    let ip = ng.children[n].bounds.center;
                                    // test it against both lines
                                    let det1 = this.getDeterminant(normal1, {x:ip.x-a.x, y:ip.y-a.y});
                                    let det2 = this.getDeterminant(normal2, {x:ip.x-b.x, y:ip.y-b.y});
                                    // pattern should be -- / ++ / -+
                                    if (Math.sign(det1) == Math.sign(det2)) {
                                        if (det1<0) {
                                            line.maskPath.removeSegments();
                                            ng.children[n].segments.forEach(s=>line.maskPath.add(s));
                                            line.maskPath.closePath();
                                        } else {
                                            newMask = ng.children[n].segments;
                                        }
                                    }
                                }
                            }
                        }

                        let newLine = this.createLine(null, split, newMask || null, line.region, null);
                        newLine.updateDataFromCanvas();
                    }

                    line.refresh();
                    line.updateDataFromCanvas();
                }
            }
        }.bind(this));
    }
    
    reverseSelection() {
        for (let i=0; i < this.selection.lines.length; i++) {
            this.selection.lines[i].reverse();
        }
    }
    
    linkSelection() {
        for (let i in this.selection.lines) {
            let line = this.selection.lines[i];
            // look for an intersection with a region
            let prev = line.region;
            
            for (let j in this.regions) {
                let region = this.regions[j];
                if (region.polygonPath.intersects(line.baselinePath) ||
                    line.baselinePath.isInside(region.polygonPath.bounds)) {
                    line.region = region;
                    //continue;
                }
            }
            if (line.region != prev) {
                this.trigger('baseline-editor:update', {
                    objType: 'line',
                    obj: line,
                    previous: {region: prev}});
            }
        }
        this.showContextMenu();
    }

    unlinkSelection() {
        for (let i in this.selection.lines) {
            let line = this.selection.lines[i];
            let prev = line.region;
            line.region = null;
            if (line.region != prev) {
                this.trigger('baseline-editor:update', {
                    objType: 'line',
                    obj: line,
                    previous: {region: prev}});
            }
        }
        this.showContextMenu();
    }

    mergeSelection() {
        /* strategy is:
          1) order the lines by their position,
             line direction doesn't matter since .join() can merge from start or end points
          2) join the lines 2 by 2 setting tolerance to the shortest distance between
             the starting and ending points of both lines.
          3) Delete the left over
        */

        if (this.selection.lines.filter(sel => sel.baselinePath === null).length > 0) {
            return;
        }
        
        this.selection.lines.sort(function(first, second) {
            // let vector = first.baselinePath.segments[1].point.subtract(first.baselinePath.firstSegment.point);
            // let rightToLeft = Math.cos(vector.angle/180*Math.PI) < 0;  // right to left
            // // if (vertical) return first.baselinePath.position.y - second.baselinePath.position.y; // td
            // if (rightToLeft) return second.baselinePath.position.x - first.baselinePath.position.x;
            // else 
            return first.baselinePath.position.x - second.baselinePath.position.x;
        });
        
        while (this.selection.lines.length > 1) {
            let l1 = this.selection.lines[0], l2 = this.selection.lines[1];
            if (l1.baselinePath !== null && l2.baselinePath != null) {
                l1.baselinePath.addSegments(l2.baselinePath.segments);
            }
            if (l1.maskPath != null && l2.maskPath != null) {
                let closeSeg = l1.maskPath.getNearestLocation(l2.maskPath.interiorPoint);
                l1.maskPath.insertSegments(closeSeg.index+1, l2.maskPath.segments.slice(0, -1));
            }

            this.selection.lines[1].delete();
        }
        if (this.selection.lines.length) {
            this.selection.lines[0].refresh();
            this.selection.lines[0].updateDataFromCanvas();
        }
    }

    getAverageLineHeight() {
        // somewhat computational intensive so we 'cache' it.
        if (this.averageLineHeight) return this.averageLineHeight;
        if (!this.lines.length) return 0;
        this.averageLineHeight = this.lines.map(l=>l.baseline && l.baseline[0][0] || 0).reduce((a,b)=>b-a)/this.lines.length;
        return this.averageLineHeight;
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
                        else return ['#0000FF', '#9A56FF', '#00FF76']; // give up
                    } else {
                        return ['#FF0000', '#FFFF00', '##FF7600'];
                    }
                } else {
                    return ['#FF0000', '#FFFF00', '#FF7600'];
                }
            } else {
                return ['#0000FF', '#9A56FF', '#00FF76'];
            }
        }
        
        // do we even need to load color thief?
        if (!(this.evenBaselinesColor && this.oddBaselinesColor&& this.oddMasksColor&& this.directionHintColor&& this.regionColor)) {
            var colorThief = new ColorThief();
            let palette = colorThief.getPalette(this.img, 5);
            let choices = chooseColors(palette);
            if (!this.evenBaselinesColor) this.evenBaselinesColor = choices[0];
            if (!this.oddBaselinesColor) this.oddBaselinesColor = choices[0];
            if (!this.oddMasksColor) this.oddMasksColor  = choices[1];
            if (!this.directionHintColor) this.directionHintColor = '#FF00AA';
            if (!this.regionColor) this.regionColor = choices[2];
        }
        
        // set the inputs
        this.evenBaselinesColorInput.value = this.evenBaselinesColor;
        this.oddBaselinesColorInput.value = this.evenBaselinesColor;
        this.oddMaskColorInput.value = this.oddMasksColor;
        this.dirHintColorInput.value = this.directionHintColor;
        this.regionColorInput.value = this.regionColor;
        this.selectedColor = 'red';
    }
}
