/*
   Baseline editor
   a javascript based baseline segmentation editor,
   requires paper.js.

   Usage:
   var segmenter = new Segmenter(img, options);
   segmenter.load([{baseline: [[0,0],[10,10]], mask: null}]);

   Options:
   lengthThreshold=15
   delayInit=false,
   deletePointBtn=null,
   deleteSelectionBtn=null,
   toggleMasksBtn=null,
   toggleLineModeBtn=null,
   splitBtn=null,
   mergeBtn=null,

 */
var lastId = 0;
function generateUniqueId() { return lastId++; };

function polyEq(poly1, poly2) {
    // compares polygons point by point
    let noPoly = (poly1 == null && poly2 == null);  // note: null is a singleton.. so we have to compare them separately
    let samePoly = (poly1 && poly2 &&
                    poly1.length != undefined && poly1.length === poly2.length &&
                    poly1.every((pt, index) => pt[0] === poly2[index][0] && pt[1] === poly2[index][1]));
    return (noPoly || samePoly);
}

function isRightClick(event) {
    return event.which === 3 || event.button === 2;
}

class SegmenterRegion {
    constructor(order, polygon, type, context, segmenter_) {
        this.id = generateUniqueId();
        this.order = order;
        this.segmenter = segmenter_;
        this.polygon = polygon;
        this.type = type;
        this.context = context;
        this.selected = false;
        this.color = this.segmenter.regionColors[type || 'None'];
        this.polygonPath = new Path({
            closed: true,
            opacity: 0.5,
            strokeColor: this.color,
            dashOffset: 5/this.segmenter.getRatio(),
            strokeWidth: 2/this.segmenter.getRatio(),
            fillColor: this.segmenter.mode == 'regions' ? this.color : null,
            selectedColor: this.segmenter.shadeColor(this.color, -50),
            visible: true,
            segments: this.polygon
        });

        this.tooltipText = this.type;
        this.segmenter.attachTooltip(this, this.polygonPath);
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
        this.polygonPath.reduce();  // removes unnecessary segments
        this.polygon = this.polygonPath.segments.map(s => [Math.round(s.point.x),
                                                           Math.round(s.point.y)]);
        if (!polyEq(previous.polygon, this.polygon)) {
            this.segmenter.addToUpdateQueue({regions: [this]});
        }
    }

    update(polygon) {
        if (polygon && polygon.length) {
            this.polygon = polygon;
            if (polygon.length == this.polygonPath.segments.length) {
                // if number of points didn't change make sure to keep selection
                for (let i in this.polygon) {
                    this.polygonPath.segments[i].point = this.polygon[i];
                }
            } else {
                this.polygonPath.removeSegments();
                this.polygonPath.addSegments(this.polygon);
            }
        }
    }

    remove() {
        this.unselect();
        this.polygonPath.remove();
        if(this.orderDisplay) this.orderDisplay.remove();

        // unlink all bound lines
        let lines = this.segmenter.lines.filter(l=>l.region && l.region.id==this.id);
        lines.forEach(l=>l.update(undefined, undefined, null, undefined));

        this.segmenter.regions.splice(this.segmenter.regions.findIndex(e => e.id == this.id), 1);
    }

    delete() {
        this.remove();
    }

    refresh() {
        this.color = this.segmenter.regionColors[this.type || 'None'];
        this.tooltipText = this.type;
        this.polygonPath.strokeColor = this.color;
        this.polygonPath.fillColor = this.segmenter.mode == 'regions' ? this.color : null;
        this.polygonPath.selectedColor = this.segmenter.shadeColor(this.color, -50);
    }

    get() {
        return {
            id: this.id,
            box: this.polygon.slice(),  // copy
            type: this.type,
            context: this.context
        };
    }
}

class SegmenterLine {
    constructor(order, baseline, mask, region, textDirection, type, context, segmenter_) {
        this.id = generateUniqueId();
        this.order = order;
        this.segmenter = segmenter_;
        this.mask = mask;
        this.region = region;
        this.context = context;
        this.selected = false;
        this.textDirection = textDirection || 'lr';
        this.type = type;
        this.directionHint = null;
        this.hintColor = this.segmenter.directionHintColors[type || 'None'];

        if (baseline) {
            if(baseline.segments) {  // already a paperjs.Path
                this.baselinePath = baseline;
            } else {
                this.baseline = baseline.map(pt=>[Math.round(pt[0]), Math.round(pt[1])]);
                this.baselinePath = new Path({
                    strokeColor: this.segmenter.baselinesColor,
                    // strokeWidth: 5/this.segmenter.getRatio(),
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

        this.tooltipText = this.type;
        let tooltipTarget = this.baseline !== null ? this.baselinePath : this.maskPath;
        this.segmenter.attachTooltip(this, tooltipTarget);

        this.refresh();
    }

    refresh() {
        this.tooltipText = this.type;
        this.hintColor = this.segmenter.directionHintColors[this.type || 'None'];
        this.showOrdering();
        this.showDirection();
        if (this.baselinePath) {
            if (this.segmenter.wideLineStrokes) {
                this.baselinePath.strokeWidth = 5/this.segmenter.getRatio();
            } else {
                this.baselinePath.strokeWidth = 1;
            }
        }
        if (this.directionHint) {
            if (this.segmenter.showDirectionHint) {
                this.directionHint.visible = true;
                this.directionHint.strokeColor = this.hintColor;
            } else {
                this.directionHint.visible = false;
            }
        }
    }

    getMaskColor() {
        return this.order % 2 ? this.segmenter.evenMasksColor: this.segmenter.oddMasksColor;
    }

    makeMaskPath() {
        this.maskPath = new Path({
            closed: true,
            opacity: 0.2,
            fillColor: this.getMaskColor(),
            selectedColor: 'black',
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
            this.maskPath.fillColor = this.segmenter.shadeColor(this.getMaskColor(), -50);
            this.maskPath.bringToFront();
        }
        if (this.baselinePath) {
            this.baselinePath.selected = true;
            this.baselinePath.bringToFront();
            this.baselinePath.strokeColor = this.segmenter.shadeColor(this.segmenter.baselinesColor, -50);
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
            this.maskPath.fillColor = this.getMaskColor();
            for (let i=0; i<this.maskPath.segments.length; i++) {
                if (this.maskPath.segments[i].point.selected) {
                    this.segmenter.removeFromSelection(this.maskPath.segments[i]);
                }
            }
        }
        if (this.baselinePath) {
            this.baselinePath.selected = false;
            this.baselinePath.strokeColor = this.segmenter.baselinesColor;
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

    update(baseline, mask, region, order) {
        if (baseline && baseline.length) {
            this.baseline = baseline;
            if (baseline.length == this.baselinePath.segments.length) {
                // make sure to keep selection
                for (let i in this.baseline) {
                    this.baselinePath.segments[i].point = this.baseline[i];
                }
            } else {
                this.baselinePath.removeSegments();
                this.baselinePath.addSegments(baseline);
            }
            /* this.baselinePath.strokeWidth = 5/this.segmenter.getRatio();
             * this.segmenter.bindLineEvents(this); */
        }
        if (mask && mask.length) {
            if (! this.maskPath) {
                this.makeMaskPath();
            }
            this.mask = mask;
            if (mask.length == this.maskPath.segments.length) {
                // make sure to keep selection
                for (let i in this.mask) {
                    this.maskPath.segments[i].point = this.mask[i];
                }
            } else {
                this.maskPath.removeSegments();
                this.maskPath.addSegments(mask);
            }
            // this.segmenter.bindMaskEvents(this);
        }
        if (region !== undefined) {
            this.region = region;
        }
        if (order != undefined) {
            this.order = order;
            if (this.orderDisplay) {
                let text = this.orderDisplay.children[2];
                text.content = this.order + 1;
            }
        }
        this.refresh();
    }

    updateDataFromCanvas() {
        let previous = {baseline: this.baseline, mask: this.mask};
        if (this.baselinePath) {
            this.baselinePath.reduce();  // removes unnecessary segments
            this.baseline = this.baselinePath.segments.map(s => [Math.round(s.point.x), Math.round(s.point.y)]);
        }
        if (this.maskPath) {
            this.maskPath.reduce();
            this.mask = this.maskPath.segments.map(s => [Math.round(s.point.x), Math.round(s.point.y)]);
        }

        if (!polyEq(previous.baseline, this.baseline) ||
            !polyEq(previous.mask, this.mask)) {
            this.segmenter.addToUpdateQueue({lines: [this]});
        }
    }

    extend(point) {
        // make sure the point is inside img boundaries
        this.segmenter.movePointInView(point, {x:0, y:0});
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
        this.remove();
    }

    reverse() {
        if (this.baselinePath) {
            let previous = {baseline: this.baseline, mask: this.mask};
            this.baselinePath.reverse();
            this.refresh();
            this.updateDataFromCanvas();
        }
    }

    createOrderDisplay(anchor) {
        let offset = 10, circle, text, region;
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

        // adds the region hint
        region = new Shape.Circle({
            x: anchor.x+5,
            y: anchor.y}, offset);
        if (this.region) region.fillColor = this.region.color;
        else region.fillColor = 'transparent';
        region.strokeColor = 'black';
        region.strokeWidth = 1;

        this.orderDisplay = new Group({
            children: [region, circle, text]
        });
        this.orderDisplay.scale(1/this.segmenter.getRatio());
        // Note: for some reason we need to reposition it after scaling
        // todo: investigate why
        text.position = anchor;
    }

    showOrdering() {
        let anchorPath = this.baselinePath?this.baselinePath:this.maskPath;
        let anchor = (this.textDirection == 'lr' ?
                      anchorPath.firstSegment.point :
                      anchorPath.lastSegment.point);

        if (!this.orderDisplay) {
            // create it if it doesnt already exists
            this.createOrderDisplay(anchor);
        } else {
            // update
            let region = this.orderDisplay.children[0],
                circle = this.orderDisplay.children[1],
                text = this.orderDisplay.children[2];
            circle.position = anchor;
            text.position = anchor;
            text.content = parseInt(this.order)+1;
            region.position = {x: anchor.x+5/this.segmenter.getRatio(), y: anchor.y};
            if (this.region) region.fillColor = this.region.color;
            else region.fillColor = 'transparent';
        }
    }

    createDirectionHint() {
        this.directionHint = new Path({
            visible: true,
            strokeWidth: Math.max(2, 4 / this.segmenter.getRatio()),
            opacity: 0.5,
            strokeColor: this.hintColor
        });
        this.segmenter.dirHintsGroup.addChild(this.directionHint);
    }

    showDirection() {
        // shows an orthogonal segment at the start of the line, length depends on line height
        if (this.baselinePath && this.baselinePath.segments.length > 1) {
            this.segmenter.linesLayer.activate();
            if (this.directionHint === null) {
                this.createDirectionHint();
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

    get() {
        return {
            id: this.id,
            context: this.context,
            baseline: this.baseline && this.baseline.slice() || null,
            mask: this.mask && this.mask.slice() || null,
            region: this.region && this.region.get() || null,
            type: this.type
        };
    }
}

export class Segmenter {
    constructor(image, {lengthThreshold=10,
                        regionAreaThreshold=20,
                        // scale = real coordinates to image coordinates
                        // for example if drawing on a 1000px wide thumbnail for a 'real' 3000px wide image,
                        // the scale would be 1/3, the container (DOM) width is irrelevant here.
                        scale=1,
                        delayInit=false,
                        disableShortcuts=false,

                        baselinesColor=null,
                        directionHintColors=null,
                        regionColors=null,

                        regionTypes=['Title', 'Main', 'Marginal', 'Illustration', 'Numbering'],
                        lineTypes=['Main', 'Interlinear'],
                        wideLineStrokes=true,
                        // todo: choose keyboard shortcuts

                        inactiveLayerOpacity=0.5,
                        maxSegments=50,
                        // when creating a line, which direction should it take.
                        defaultTextDirection='lr',
                        // field to store and reuse in output from loaded data
                        // can be set to null to disable behavior
                        idField='id'} = {}) {
        this.loaded = false;
        this.img = image;
        this.mode = 'lines'; // | 'regions'
        this.lines = [];
        this.regions = [];

        this.regionTypes = ['None'].concat(regionTypes);
        this.lineTypes = ['None'].concat(lineTypes);

        this.selection = {lines:[], segments:[], regions:[]};
        this.defaultTextDirection = defaultTextDirection;

        this.scale = scale;
        this.canvas = document.createElement('canvas');
        this.canvas.style.position = 'absolute';
        this.canvas.style.top = 0;
        this.canvas.style.left = 0;

        // paper.js helpers
        this.inactiveLayerOpacity = inactiveLayerOpacity;
        this.linesLayer = this.regionsLayer = this.orderingLayer = null;
        this.regionsGroup = null;

        this.idField = idField;
        this.disableShortcuts = disableShortcuts;

        // create a dummy tag for event bindings
        this.events = document.createElement('div');
        this.events.setAttribute('id', 'baseline-editor-events');
        document.body.appendChild(this.events);

        // this.raster = null;
        this.img.parentNode.insertBefore(this.canvas, this.img);

        this.baselinesColor=baselinesColor;
        /* this.evenMasksColor=baselinesColor;
         * this.evenMasksColor=evenMasksColor;
         * this.oddMasksColor=oddMasksColor; */
        this.directionHintColors=directionHintColors || {};
        this.regionColors=regionColors || {};
        this.maxSegments = maxSegments;

        // the minimal length in pixels below which the line will be removed automatically
        this.lengthThreshold = lengthThreshold;
        this.regionAreaThreshold = regionAreaThreshold;
        this.showMasks = false;
        this.showLineNumbers = false;
        this.showDirectionHint = true;
        this.wideLineStrokes = wideLineStrokes;

        this.selecting = null;
        this.spliting = false;
        this.copy = null;

        // menu btns
        this.toggleMasksBtn = document.getElementById('be-toggle-masks');
        this.toggleLineModeBtn = document.getElementById('be-toggle-line-mode');
        this.toggleOrderingBtn = document.getElementById('be-toggle-order');
        this.toggleRegionModeBtn = document.getElementById('be-toggle-regions');
        this.splitBtn = document.getElementById('be-split-lines');

        // contextual btns
        this.deletePointBtn = document.getElementById('be-delete-point');
        this.deleteSelectionBtn = document.getElementById('be-delete-selection');
        this.mergeBtn = document.getElementById('be-merge-selection');
        this.reverseBtn = document.getElementById('be-reverse-selection');
        this.linkRegionBtn = document.getElementById('be-link-region');
        this.unlinkRegionBtn = document.getElementById('be-unlink-region');
        this.setTypeBtn = document.getElementById('be-set-type');

        // editor settings;
        this.baselinesColorInput = document.getElementById('be-bl-color');
        this.evenMasksColorInput = document.getElementById('be-even-mask-color');
        this.oddMasksColorInput = document.getElementById('be-odd-mask-color');
        this.dirHintColorInputs = [];
        for (let index in this.lineTypes) {
            this.dirHintColorInputs.push(document.getElementById('be-dir-color-'+index));
        }
        this.regionColorInputs = [];
        for (let index in this.regionTypes) {
            this.regionColorInputs.push(document.getElementById('be-reg-color-'+index));
        }

        // create a menu for the context buttons
        this.contextMenu = document.getElementById('context-menu');
        if (!this.contextMenu) {
            document.createElement('div');
            this.contextMenu.id = 'context-menu';
        }
        if (this.linkRegionBtn) this.contextMenu.appendChild(this.linkRegionBtn);
        if (this.unlinkRegionBtn) this.contextMenu.appendChild(this.unlinkRegionBtn);
        if (this.mergeBtn) this.contextMenu.appendChild(this.mergeBtn);
        if (this.reverseBtn) this.contextMenu.appendChild(this.reverseBtn);
        if (this.setTypeBtn) this.contextMenu.appendChild(this.setTypeBtn);
        if (this.deletePointBtn) this.contextMenu.appendChild(this.deletePointBtn);
        if (this.deleteSelectionBtn) this.contextMenu.appendChild(this.deleteSelectionBtn);

        this.tooltip = document.getElementById('info-tooltip');

        this.createTypeSelects();
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
        this.trigger('baseline-editor:delete', {
            lines: this.selection.lines.map(l=>l.get()),
            regions: this.selection.regions.map(r=>r.get())
        });

        // optimisticaly removes everything
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
        if (this.toggleLineModeBtn) {
            this.toggleLineModeBtn.addEventListener('click', function(event) {
                this.toggleLineMode();
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
        if (this.setTypeBtn) this.setTypeBtn.addEventListener('click', function(event) {
            this.showTypeSelect();
        }.bind(this));
        if (this.toggleOrderingBtn) this.toggleOrderingBtn.addEventListener('click', function(ev) {
            this.toggleOrdering();
        }.bind(this));

        // colors
        if(this.baselinesColorInput) this.baselinesColorInput.addEventListener('change', function(ev) {
            this.baselinesColor = ev.target.value;
            this.linesGroup.strokeColor = ev.target.value;
            this.trigger('baseline-editor:settings', {name: 'color-baselines',
                                                      value: ev.target.value});
        }.bind(this));

        if (this.dirHintColorInputs) {
            for (let index in this.dirHintColorInputs) {
                let input = this.dirHintColorInputs[index];
                input.addEventListener('change', function(ev) {
                    let type = this.lineTypes[index];
                    this.directionHintColors[type] = ev.target.value;
                    if (type == 'None') type = null;  // switch to null for comparison
                    for (let index in this.lines) {
                        let line = this.lines[index];
                        if (line.type == type) {
                            line.refresh();
                        }
                    }
                    this.trigger('baseline-editor:settings', {name: 'color-directions',
                                                              value: this.directionHintColors});
                }.bind(this));
            }
        }
        if (this.regionColorInputs) {
            for (let index in this.regionColorInputs) {
                let input = this.regionColorInputs[index];
                input.addEventListener('change', function(ev) {
                    let type = this.regionTypes[index];
                    this.regionColors[type] = ev.target.value;
                    if (type == 'None') type = null;  // switch to null for comparison
                    for (let index in this.regions) {
                        let region = this.regions[index];
                        if (region.type == type) {
                            region.refresh();
                        }
                    }
                    this.trigger('baseline-editor:settings', {name: 'color-regions',
                                                              value: this.regionColors});
                }.bind(this));
            }
        }

        document.addEventListener('keydown', function(event) {
            if (this.disableShortcuts) return;
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
                if (this.splitBtn) {
                    this.splitBtn.classList.toggle('btn-warning');
                    this.splitBtn.classList.toggle('btn-success');
                }
                this.setCursor();
            } else if (event.keyCode == 73) { // K
                this.reverseSelection();
            } else if (event.keyCode == 74) { // J (for join)
                this.mergeSelection();
            } else if (event.keyCode == 77) { // M
                this.toggleLineMode();
            } else if (event.keyCode == 76) { // L
                this.toggleOrdering();
            } else if (event.keyCode == 82) { // R
                this.toggleRegionMode();
            } else if (event.keyCode == 89) { // Y
                this.linkSelection();
            } else if (event.keyCode == 85) { // U
                this.unlinkSelection();
            } else if (event.keyCode ==  84) {  // T
                this.showTypeSelect();
                event.preventDefault();  // avoid selecting an option starting with T
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

        // setup outbound events
        this.updateQueue = {lines: [], regions:[]};
        paper.view.onFrame = function(ev) {
            this.consumeUpdateQueue();
        }.bind(this);

        this.regionsGroup = new paper.Group();
        this.linesGroup = new paper.Group();
        this.evenMasksGroup = new paper.Group();
        this.oddMasksGroup = new paper.Group();
        this.dirHintsGroup = new paper.Group();

        this.linesLayer = paper.project.activeLayer;
        this.regionsLayer = new paper.Layer();
        this.orderingLayer = new paper.Layer();
        this.orderingLayer.visible = this.showLineNumbers;
        if (this.mode == 'lines') {
            this.evenMasksGroup.bringToFront();
            this.oddMasksGroup.bringToFront();
            this.linesGroup.bringToFront();
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

        this.canvas.style.width = this.img.width;
        this.canvas.style.height = this.img.height;

        var tool = new Tool();
        this.setColors(this.img);
        this.setCursor();

        // this.raster = new Raster(this.img);  // Note: this seems to slow down everything significantly
        // this.raster.position = view.center;
        // this.img.style.display = 'hidden';

        // hide the tooltip on leaving the area
        this.canvas.addEventListener('mouseleave', function() {
            this.tooltip.style.display = 'none';
        }.bind(this));

        this.tool = tool;
        this.tool.activate();
        this.resetToolEvents();

        this.loaded = true;
    }

    createLine(order, baseline, mask, region, type, context, postponeEvents) {
        if (this.idField) {
            if (context === undefined || context === null) {
                context = {};
            }
            if (context[this.idField] === undefined) {
                // make sure the client receives a value for its id, even if it's null for a new line
                context[this.idField] = null;
            }
        }

        if (!order) order = parseInt(this.getLineMaxOrder()) + 1;
        this.linesLayer.activate();
        var line = new SegmenterLine(order, baseline, mask, region,
                                     this.defaultTextDirection, type,
                                     context, this);
        this.linesGroup.addChild(line.baselinePath);
        if (line.maskPath) {
            if (line.order%2)this.evenMasksGroup.addChild(line.maskPath);
            else this.oddMasksGroup.addChild(line.maskPath);
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

    createRegion(order, polygon, type, context, postponeEvents) {
        if (this.idField) {
            if (context === undefined || context === null) {
                context = {};
            }
            if (context[this.idField] === undefined) {
                // make sure the client receives a value for its id, even if it's null for a new region
                context[this.idField] = null;
            }
        }
        if (!order) order = parseInt(this.getMaxRegionOrder()) + 1;
        this.regionsLayer.activate();
        var region = new SegmenterRegion(order, polygon, type, context, this);
        if (!postponeEvents) this.bindRegionEvents(region);
        this.regions.push(region);
        this.regionsGroup.addChild(region.polygonPath);
        return region;
    }

    finishRegion(region) {
        if (Math.abs(region.polygonPath.area) < this.regionAreaThreshold) {
            region.remove();
        } else {
            this.bindRegionEvents(region);
            region.updateDataFromCanvas();
        }
        this.resetToolEvents();
    }

    bindRegionEvents(region) {
        region.polygonPath.onMouseDown = function(event) {
            if (event.event.ctrlKey ||
                this.spliting ||
                // this.selecting ||
                isRightClick(event.event) ||
                this.mode != 'regions') return;

            // if what we are clicking on is already selected,
            // check there isn't something below
            if (region.selected) {
                let hit;
                for (let i=0; i<this.regions.length; i++) {
                    if (this.regions[i] != region) {
                        hit = this.regions[i].polygonPath.hitTest(event.point);
                        if (hit) {
                            this.selecting = this.regions[i];
                            break;
                        }
                    }
                }
                if (!hit) this.selecting = region;
            } else {
                this.selecting = region;
            }

            var dragging = region.polygonPath.getNearestLocation(event.point).segment;
            this.tool.onMouseDrag = function(event) {
                this.selecting = region;
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
                this.onMouseUp(event);
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
                    this.spliting ||
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
                    this.onMouseUp(event);
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
                    this.spliting ||
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
                    this.onMouseUp(event);
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
        this.tool.onMouseUp = null; //this.onMouseUp.bind(this);
        this.tool.onMouseDrag = this.onMouseDrag.bind(this);
        this.tool.onMouseMove = null;
    }

    attachTooltip(obj, target) {
        target.onMouseEnter = function(event) {
            if (obj.tooltipText) {
                this.tooltip.textContent = obj.tooltipText;
                this.tooltip.style.display = 'block';
            } else {
                this.tooltip.style.display = 'none';
            }

        }.bind(this);
        target.onMouseLeave = function(event) {
            this.tooltip.style.display = 'none';
        }.bind(this);
    }

    multiMove(event) {
        var delta = event.delta;
        if (this.mode == 'lines') {
            if (this.selection.segments.length) {
                for (let i in this.selection.segments) {
                    this.movePointInView(this.selection.segments[i].point, delta);
                }
                for (let i in this.selection.lines) {
                    // refresh hints positions
                    this.selection.lines[i].refresh();
                }
            } else {
                // move the entire line
                for (let i in this.selection.lines) {
                    let line = this.selection.lines[i];
                    if (line.baselinePath) {
                        for (let j in line.baselinePath.segments) {
                            this.movePointInView(line.baselinePath.segments[j].point, delta);
                        }
                    }
                    if (line.maskPath) {
                        for (let j in line.maskPath.segments) {
                            this.movePointInView(line.maskPath.segments[j].point, delta);
                        }
                    }
                    // refresh hint positions
                    line.refresh();
                }
            }
        } else if (this.mode == 'regions') {
            if (this.selection.segments.length) {
                for (let i in this.selection.segments) {
                    this.movePointInView(this.selection.segments[i].point, delta);
                }
            } else {
                for (let i in this.selection.regions) {
                    let region = this.selection.regions[i];
                    for (let j in region.polygonPath.segments) {
                        this.movePointInView(region.polygonPath.segments[j].point, delta);
                    }
                }
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
        if (!this.selecting) {
            if (event.event.ctrlKey) return;
            if (this.spliting) {
                this.startCuter(event);
            } else if (event.event.shiftKey) {
                // lasso selection tool
                this.startLassoSelection(event);
            }  else if (this.mode == 'regions') {
                this.startNewRegion(event);
            }  else {  // mode = 'lines'
                // create a new line
                this.startNewLine(event);
            }
        }
    }

    onMouseUp(event) {
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
        } else if (this.hasSelection()) {
            this.purgeSelection();
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
        let newLine = this.createLine(null, [clickLocation], null, region, null, null, true);
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
        let newRegion = this.createRegion(null, [
            [event.point.x, event.point.y],
            [event.point.x, event.point.y+1],
            [event.point.x+1, event.point.y+1],
            [event.point.x+1, event.point.y]
        ], null, null, true);

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
            let pt = {x: event.point.x, y: event.point.y};
            this.movePointInView(pt, {x: 0, y:0}); // make sure it stays inside boundaries
            newRegion.polygonPath.segments[1].point.y = pt.y;
            newRegion.polygonPath.segments[2].point.x = pt.x;
            newRegion.polygonPath.segments[2].point.y = pt.y;
            newRegion.polygonPath.segments[3].point.x = pt.x;
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
            if (this.mode == 'lines') {
                this.splitLinesByPath(clip);
            } else if (this.mode == 'regions') {
                this.splitRegionsByPath(clip);
            }
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

    getRatio() {
        let bounds = this.img.getBoundingClientRect();
        let imgRatio = (bounds.width / this.img.naturalWidth);
        return imgRatio * this.scale;
    }

    refresh() {
        /*
           Call when either the available space or the source image size changed.
         */
        if (paper.view) {
            let bounds = this.img.getBoundingClientRect();
            let imgRatio = (bounds.width / this.img.naturalWidth);
            let ratio = imgRatio/paper.view.zoom*this.scale;
            if (paper.view.viewSize[0] != bounds.width &&
                paper.view.viewSize[1] != bounds.height) {
                paper.view.viewSize = [bounds.width, bounds.height];
                paper.view.scale(ratio, [0, 0]);
            }
            // recalculate average line heights for lines without masks
            this.resetLineHeights();
            this.applyRegionMode();
        }
    }

    loadLine(line, region) {
        let context = {};
        if ((line.baseline !== null && line.baseline.length) ||
            (line.mask !== null && line.mask.length)) {
            if (this.idField) context[this.idField] = line[this.idField];
            if (!line.baseline) this.toggleMasks(true);
            return this.createLine(null, line.baseline, line.mask,
                                   region, line.type, context);
        } else {
            console.log('EDITOR SKIPPING invalid line: ', line);
            return null;
        }
    }

    loadRegion(region) {
        let context = {};
        if (this.idField) context[this.idField] = region[this.idField];
        let r = this.createRegion(null, region.box, region.type, context);
        for (let j in region.lines) {
            this.loadLine(region.lines[j], r);
        }
        return r;
    }

    load(data) {
        /* Loads a list of lines containing each a baseline polygon and a mask polygon
         * [{baseline: [[x1, y1], [x2, y2], ..], mask:[[x1, y1], [x2, y2], ]}, {..}] */
        for (let i in data.regions) {
            this.loadRegion(data.regions[i]);
        }

        // now load orphan lines
        for (let i in data.lines) {
            this.loadLine(data.lines[i], null);
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

    toggleLineMode() {
        // wide: default mode
        // mask: show the boundary of the line
        // slim: set the strokeWidth at 1px
        if (this.showMasks) { // mask -> slim
            this.toggleMasks(false);
            this.toggleLineStrokes(false);

            this.toggleLineModeBtn.classList.add('btn-secondary');
            this.toggleLineModeBtn.classList.remove('btn-success');
        } else {
            if (!this.wideLineStrokes) { // slim -> wide
                this.toggleMasks(false);
                this.toggleLineStrokes(true);

                this.toggleLineModeBtn.classList.add('btn-info');
                this.toggleLineModeBtn.classList.remove('btn-secondary');
            } else { // wide -> mask
                this.toggleMasks(true);
                this.toggleLineStrokes(true);

                this.toggleLineModeBtn.classList.add('btn-success');
                this.toggleLineModeBtn.classList.remove('btn-info');
            }
        }
    }

    toggleLineStrokes(force) {
        // wide / slim
        if (force != undefined) this.wideLineStrokes = force;
        else this.wideLineStrokes = !this.wideLineStrokes;

        this.showDirectionHint = this.wideLineStrokes;

        for (let i in this.lines) {
            this.lines[i].refresh();
        }
    }

    toggleMasks(force) {
        if (force !== undefined) this.showMasks = force;
        else this.showMasks = !this.showMasks;
        if (this.toggleMasksBtn) {
            if (this.showMasks) {
                this.toggleMasksBtn.classList.add('btn-success');
                this.toggleMasksBtn.classList.remove('btn-info');
            } else {
                this.toggleMasksBtn.classList.add('btn-info');
                this.toggleMasksBtn.classList.remove('btn-success');
            }
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

    applyRegionMode() {
        if (this.mode == 'regions') {
            for(let index in this.regions)  {
                let region = this.regions[index];
                region.polygonPath.strokeColor = this.shadeColor(region.color, -50);
                region.polygonPath.fillColor = region.color;
            }
            this.regionsGroup.bringToFront();
            this.regionsLayer.opacity = 1;
            this.linesLayer.opacity = this.inactiveLayerOpacity;
        } else {
            // this.regionsGroup.strokeColor = this.regionColor;
            for(let index in this.regions)  {
                let region = this.regions[index];
                region.polygonPath.strokeColor = region.color;
            }
            this.regionsGroup.fillColor = null;
            this.regionsGroup.sendToBack();
            this.regionsLayer.opacity = this.inactiveLayerOpacity;
            this.linesLayer.opacity = 1;
        }
    }

    toggleRegionMode() {
        this.purgeSelection();
        if (this.mode == 'lines') {
            this.mode = 'regions';
        } else {
            this.mode = 'lines';
        }
        this.applyRegionMode();
        if (this.toggleRegionModeBtn) {
            this.toggleRegionModeBtn.classList.toggle('btn-info');
            this.toggleRegionModeBtn.classList.toggle('btn-success');
        }
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

            // we can only merge if all lines contain a baseline
            if (this.selection.lines.filter(l => l.baseline !== null).length > 1) {
                this.mergeBtn.style.display = 'block';
            }
            if (this.regions.length > 0) {
                if (this.selection.lines.filter(l => l.region == null).length > 0) {
                    // at least one line without region
                    this.linkRegionBtn.style.display = 'block';
                }
                if (this.selection.lines.filter(l => l.region !== null).length > 0) {
                    // at least one line with a region
                    this.unlinkRegionBtn.style.display = 'block';
                }
            }

            if (this.lineTypes.length) this.setTypeBtn.style.display = 'block';
            else this.setTypeBtn.style.display = 'none';
        }

        if (this.selection.regions.length) {
            if (this.regionTypes.length) this.setTypeBtn.style.display = 'block';
            else this.setTypeBtn.style.display = 'none';
        }

        if (this.selection.segments.length) {
            if (this.deletePointBtn) this.deletePointBtn.style.display = 'block';
        }

        this.contextMenu.style.display = 'block';
    }

    showTypeSelect() {
        if (this.selection.lines.length) {
            this.lineTypesSelect.style.display = 'block';
            this.lineTypesSelect.style.top = this.setTypeBtn.offsetTop+'px';
            this.lineTypesSelect.style.left = this.setTypeBtn.offsetLeft+this.setTypeBtn.clientWidth+10+'px';
            this.lineTypesSelect.focus();
            // if all type are the same selects it in the type selector
            if (this.selection.lines.every((line, i, arr) => line.type === arr[0].type)) {
                this.lineTypesSelect.value = this.selection.lines[0].type || 'None';
            } else {
                this.lineTypesSelect.value = 'None';
            }
        } else if (this.selection.regions.length) {
            this.regionTypesSelect.style.display = 'block';
            this.regionTypesSelect.style.top = this.setTypeBtn.offsetTop+'px';
            this.regionTypesSelect.style.left = this.setTypeBtn.offsetLeft+this.setTypeBtn.clientWidth+10+'px';
            this.regionTypesSelect.focus();
            // if all type are the same selects it in the type selector
            if (this.selection.regions.every((reg, i, arr) => reg.type === arr[0].type)) {
                this.regionTypesSelect.value = this.selection.regions[0].type || 'None';
            } else {
                this.regionTypesSelect.value = 'None';
            }
        } else {
            // avoid unbinding keyboard then
            return;
        }

        var self = this;  // mandatory for unbinding

        function unbindKb() {
            document.removeEventListener('keydown', bindKb);
            self.disableShortcuts = false;
            self.regionTypesSelect.blur();
            self.lineTypesSelect.blur();
        }

        function bindKb(ev) {
            if (ev.keyCode == 27) {  // escape
                unbindKb.bind(this)();
                ev.stopPropagation();
            } else if (ev.keyCode == 13) {  // enter
                self.setSelectionType(document.activeElement.value);
                unbindKb.bind(this)();
                ev.stopPropagation();
            } else {
                let num = Number(ev.key);
                if (!isNaN(num) && num <= document.activeElement.childElementCount) {
                    self.setSelectionType(document.activeElement.children[num].value);
                    unbindKb.bind(this)();
                    ev.stopPropagation();
                }
            }
        }

        // disable other shortcuts
        this.disableShortcuts = true;
        document.addEventListener('keydown', bindKb);
    }

    createTypeSelects() {
        this.regionTypesSelect = document.createElement('select');
        this.regionTypesSelect.style.position = 'absolute';
        this.regionTypesSelect.autocomplete = "off";
        this.regionTypesSelect.style.display = 'none';
        this.regionTypes.forEach(function(type, i) {
            let opt = document.createElement('option');
            opt.value = type;
            opt.text = type + ' ('+i+')';
            this.regionTypesSelect.appendChild(opt);
        }.bind(this));
        this.regionTypesSelect.size = this.regionTypes.length+1;
        this.contextMenu.appendChild(this.regionTypesSelect);
        this.regionTypesSelect.addEventListener('blur', function(ev) {
            this.regionTypesSelect.style.display = 'none';
            this.disableShortcuts = false;
        }.bind(this));
        this.regionTypesSelect.addEventListener('dblclick', function() {
            this.setSelectionType(this.regionTypesSelect.value);
            this.disableShortcuts = false;
            this.regionTypesSelect.blur();
        }.bind(this));

        this.lineTypesSelect = document.createElement('select');
        this.lineTypesSelect.style.position = 'absolute';
        this.lineTypesSelect.autocomplete = "off";
        this.lineTypesSelect.style.display = 'none';
        this.lineTypes.forEach(function(type, i) {
            let opt = document.createElement('option');
            opt.value = type;
            opt.text = type + ' ('+i+')';
            this.lineTypesSelect.appendChild(opt);
        }.bind(this));
        this.lineTypesSelect.size = this.lineTypes.length+1;
        this.contextMenu.appendChild(this.lineTypesSelect);
        this.lineTypesSelect.addEventListener('blur', function(ev) {
            this.lineTypesSelect.style.display = 'none';
            this.disableShortcuts = false;
        }.bind(this));
        this.lineTypesSelect.addEventListener('dblclick', function() {
            this.setSelectionType(this.lineTypesSelect.value);
            this.disableShortcuts = false;
            this.lineTypesSelect.blur();
        }.bind(this));
    }

    setSelectionType(value) {
        if (value == 'None') value = null;
        for (let i=0; i<this.selection.lines.length; i++) {
            let line = this.selection.lines[i];
            if (line.type != value) {
                line.type = value;
                this.addToUpdateQueue({lines: line});
                line.refresh();
            }
        }
        for (let i=0; i<this.selection.regions.length; i++) {
            let region = this.selection.regions[i];
            if (region.type != value) {
                region.type = value;
                this.addToUpdateQueue({regions: this.selection.regions[i]});
                region.refresh();
            }
        }
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
        clip.strokeWidth = Math.max(2, 2/this.getRatio());
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
                if (line.baselinePath) allSegments = line.baselinePath.segments.concat(line.maskPath.segments);
                else allSegments = line.maskPath.segments;
            } else {
                allSegments = line.baselinePath.segments;
            }
            this.clipSelectPoly(clip, allSegments, tmpSelected);
            if ((line.baselinePath && line.baselinePath.intersects(clip)) ||
                (line.baselinePath && line.baselinePath.isInside(clip.bounds)) ||
                (this.showMasks && line.maskPath && line.maskPath.intersects(clip))) line.select();
            else if (allLines.length == this.lines.length) line.unselect();
        }
    }

    splitHelper(clip, event) {
        if (this.mode == 'lines') {
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
        } else if (this.mode == 'regions') {
            this.regions.forEach(function(region) {
                let inter = region.polygonPath.intersect(clip);
                inter.strokeColor = 'red';
                inter.strokeWidth = 2;
                inter.fillColor = 'red';
                inter.removeOnDrag().removeOnUp();
            }.bind(this));
        }
    }

    getLineMaxOrder() {
        if (!this.lines.length) return -1;
        return this.lines.map(l=>l.order).reduce((a,b)=>Math.max(a, b));
    }

    getMaxRegionOrder() {
        if (!this.regions.length) return -1;
        return this.regions.map(r=>r.order).reduce((a,b)=>Math.max(a, b));
    }

    getDeterminant(v1, v2) {
        let matrix = [[v1.x, v2.x], [v1.y, v2.y]];
        return math.det(matrix);
    }

    splitRegionsByPath(path) {
        this.regions.forEach(function(region) {
            let intersections = region.polygonPath.getIntersections(path);
            if (intersections.length == 2) {
                // remove everything in the selection rectangle
                let newPath = region.polygonPath.subtract(path, {insert: true});
                region.polygonPath.removeSegments();
                newPath.segments.forEach(s=>region.polygonPath.add(s));
                newPath.remove();
            } else if (intersections.length > 2) {
                let compound = region.polygonPath.subtract(path, {insert: true});
                region.polygonPath.removeSegments();
                compound.children[0].segments.forEach(s=>region.polygonPath.add(s));
                for (let i=1;i<compound.children.length;i++) {
                    let newRegion = this.createRegion(null, compound.children[i].segments,
                                                      region.type, null, false);
                    newRegion.updateDataFromCanvas();
                    compound.children[i].remove();
                }
                compound.remove();
            }
            region.refresh();
            region.updateDataFromCanvas();
        }.bind(this));
    }

    splitLinesByPath(path) {
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

                        let newLine = this.createLine(null, split, newMask || null, line.region, line.type, null);
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
                let center = line.baselinePath.getPointAt(line.baselinePath.length/2);
                if (region.polygonPath.contains(center)) {
                    line.region = region;
                    continue;
                }
            }
            if (line.region != prev) {
                this.addToUpdateQueue({lines: [line]});
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
                this.addToUpdateQueue({lines: [line]});
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

        this.trigger('baseline-editor:delete', {
            lines: this.selection.lines.slice(1)
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

    addToUpdateQueue(items) {  // {lines:[], regions:[]}
        this.updateQueue.lines = this.updateQueue.lines.concat(items.lines || []);
        this.updateQueue.regions = this.updateQueue.regions.concat(items.regions || []);
    }

    consumeUpdateQueue() {
        // make copies to void race conditions
        let lines = this.updateQueue.lines.map(l=>l.get());
        let regions = this.updateQueue.regions.map(r=>r.get());

        // empty the queue asap
        this.updateQueue = {lines: [], regions: []};

        if (lines.length || regions.length) {
            this.trigger('baseline-editor:update', {
                lines: lines,
                regions: regions
            });
        }
    }

    getAverageLineHeight() {
        // somewhat computational intensive so we 'cache' it.
        if (!this.averageLineHeight) this.computeAverageLineHeight();
        return this.averageLineHeight;
    }

    computeAverageLineHeight() {
        if (this.lines.length == 0) {
            this.averageLineHeight = 0;
        } else if (this.lines.length == 1) {
            this.averageLineHeight = 20 / this.scale;
        } else {
            this.averageLineHeight = Math.abs(
                this.lines
                    .map(l=>l.baseline && l.baseline[0][0] || 0)
                    .reduce((a,b)=>b-a) / this.lines.length / 2);
        }
    }

    resetLineHeights() {
        this.computeAverageLineHeight();
        this.lines.forEach(function(line) {
            line.refresh();
        }.bind(this));
    }

    setCursor(style) {
        if (style) {
            this.canvas.style.cursor = style;
        } else {
            this.canvas.style.cursor = this.spliting?'crosshair':'copy';
        }
    }

    shadeColor(color, percent) {
        let R = parseInt(color.substring(1,3),16);
        let G = parseInt(color.substring(3,5),16);
        let B = parseInt(color.substring(5,7),16);
        R = Math.min(255, parseInt(R * (100 + percent) / 100));
        G = Math.min(255, parseInt(G * (100 + percent) / 100));
        B = Math.min(255, parseInt(B * (100 + percent) / 100));
        let RR = ((R.toString(16).length==1)?"0"+R.toString(16):R.toString(16));
        let GG = ((G.toString(16).length==1)?"0"+G.toString(16):G.toString(16));
        let BB = ((B.toString(16).length==1)?"0"+B.toString(16):B.toString(16));
        return "#"+RR+GG+BB;
    }

    changeHue(rgb, degree) {
        // exepcts a string and returns an object
        function rgbToHSL(rgb) {
            // strip the leading # if it's there
            rgb = rgb.replace(/^\s*#|\s*$/g, '');

            // convert 3 char codes --> 6, e.g. `E0F` --> `EE00FF`
            if(rgb.length == 3){
                rgb = rgb.replace(/(.)/g, '$1$1');
            }

            var r = parseInt(rgb.substr(0, 2), 16) / 255,
                g = parseInt(rgb.substr(2, 2), 16) / 255,
                b = parseInt(rgb.substr(4, 2), 16) / 255,
                cMax = Math.max(r, g, b),
                cMin = Math.min(r, g, b),
                delta = cMax - cMin,
                l = (cMax + cMin) / 2,
                h = 0,
                s = 0;

            if (delta == 0) {
                h = 0;
            }
            else if (cMax == r) {
                h = 60 * (((g - b) / delta) % 6);
            }
            else if (cMax == g) {
                h = 60 * (((b - r) / delta) + 2);
            }
            else {
                h = 60 * (((r - g) / delta) + 4);
            }

            if (delta == 0) {
                s = 0;
            }
            else {
                s = (delta/(1-Math.abs(2*l - 1)))
            }

            return {
                h: h,
                s: s,
                l: l
            }
        }

        // expects an object and returns a string
        function hslToRGB(hsl) {
            var h = hsl.h,
                s = hsl.s,
                l = hsl.l,
                c = (1 - Math.abs(2*l - 1)) * s,
                x = c * ( 1 - Math.abs((h / 60 ) % 2 - 1 )),
                m = l - c/ 2,
                r, g, b;

            if (h < 60) {
                r = c;
                g = x;
                b = 0;
            }
            else if (h < 120) {
                r = x;
                g = c;
                b = 0;
            }
            else if (h < 180) {
                r = 0;
                g = c;
                b = x;
            }
            else if (h < 240) {
                r = 0;
                g = x;
                b = c;
            }
            else if (h < 300) {
                r = x;
                g = 0;
                b = c;
            }
            else {
                r = c;
                g = 0;
                b = x;
            }

            r = normalize_rgb_value(r, m);
            g = normalize_rgb_value(g, m);
            b = normalize_rgb_value(b, m);

            return rgbToHex(r,g,b);
        }

        function normalize_rgb_value(color, m) {
            color = Math.floor((color + m) * 255);
            if (color < 0) {
                color = 0;
            }
            return color;
        }

        function rgbToHex(r, g, b) {
            return "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
        }

        var hsl = rgbToHSL(rgb);
        hsl.h += degree;
        if (hsl.h > 360) {
            hsl.h -= 360;
        }
        else if (hsl.h < 0) {
            hsl.h += 360;
        }
        return hslToRGB(hsl);
    }

    setColors() {
        var choices = ['#0000FF', '#9A56FF', '#11FF76'];
        if (this.baselinesColor == null) this.baselinesColor = choices[0];
        this.evenMasksColor = this.baselinesColor;
        this.oddMasksColor = this.changeHue(this.baselinesColor, 30);

        for (let index in this.lineTypes) {
            let type = this.lineTypes[index];
            if (this.directionHintColors[type] == null) {
                this.directionHintColors[type] = this.changeHue(choices[1], 3*(index+1));
            }
        }
        for (let index in this.regionTypes) {
            let type = this.regionTypes[index];
            if (this.regionColors[type] == null) {
                this.regionColors[type] = this.changeHue(choices[2], 3*(index+1));
            }
        }

        // set the inputs
        if(this.baselinesColorInput) this.baselinesColorInput.value = this.baselinesColor;
        for (let index in this.dirHintColorInputs) {
            let input = this.dirHintColorInputs[index];
            input.value = this.directionHintColors[this.lineTypes[index]];
        }
        for (let index in this.regionColorInputs) {
            let input = this.regionColorInputs[index];
            input.value = this.regionColors[this.regionTypes[index]];
        }
    }
}

window.Segmenter = Segmenter;
