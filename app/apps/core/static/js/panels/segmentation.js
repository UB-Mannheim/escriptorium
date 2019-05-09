// TODO: choose colors based on average color of image
var colors = ['blue', 'green', 'cyan', 'indigo', 'purple', 'pink', 'orange', 'yellow', 'teal'];
class Box {
    constructor(type, part, obj, imgRatio) {
        this.type = type; // can be either block or line
        this.part = part;
        this.pk = obj.pk || null;
        this.box = obj.box;
        this.updateApi();
        this.order = obj.order;
        this.block = this.part.blocks.find(function(block) {
            return block.pk == obj.block;
        });
        this.setRatio(imgRatio);
        this.changed = false;
        this.click = {x: null, y:null};
        this.originalWidth = (obj.box[2] - obj.box[0]) * this.ratio;
        this.$container = $('#seg-panel .img-container');
        var $box = $('<div class="box '+this.type+'-box"> <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>'+(DEBUG?this.order:'')+'</div>');
        var color;
        if (this.type == 'block') {
            color = colors[this.order % colors.length];
            $box.css({backgroundColor: color});
        } else if (this.type == 'line') {
            if (this.block == null) { color = 'red'; }
            else { color = colors[this.block.order % colors.length]; }
            $box.css({border: '1px solid '+color});
            if (this.order%2 == 0) {
                $box.css('filter', 'invert(100%)');
            }
        }
        $box.draggable({
            // disabled: true,
            containment: 'parent',
            cursor: "grab",
            stop: $.proxy(function(ev) {
                this.changed = true;
                this.save();
            }, this),
            // this is necessary because WheelZoom make it jquery-ui drag jump around
            start: $.proxy(function(ev) {
                this.click.x = ev.clientX;
                this.click.y = ev.clientY;
            }, this),
            drag: $.proxy(function(ev, ui) {
                var original = ui.originalPosition;
                var left = (ev.clientX - this.click.x + original.left - zoom.pos.x) / zoom.scale;
                var top = (ev.clientY - this.click.y + original.top - zoom.pos.y) / zoom.scale;
                ui.position = {
                    left: left,
                    top: top
                };
                var tl = $('#trans-box-line-'+this.pk).data('TranscriptionLine');
                var box = this.getBox();
                if (tl) {
                    tl.box = box;
                    tl.setPosition();
                }
                $('.overlay').css({
                    left: box[0]*this.ratio + 'px',
                    top: box[1]*this.ratio + 'px',
                    width: (box[2] - box[0])*this.ratio+'px',
                    height: (box[3] - box[1])*this.ratio+'px'
                });
            }, this)
        });
        $box.resizable({
            // disabled: true,
            stop: $.proxy(function(ev) {
                this.changed = true;
                this.save();
                this.resizingLine = null;
            }, this),
            start: $.proxy(function(ev) {
                this.click.x = ev.clientX;
                this.click.y = ev.clientY;
                this.resizingLine = $('#trans-box-line-'+this.pk).data('TranscriptionLine');
            }, this),
            resize: $.proxy(function(ev, ui) {
                ui.size.width = (ev.clientX - this.click.x) / zoom.scale + ui.originalSize.width;
                ui.size.height = (ev.clientY - this.click.y) / zoom.scale + ui.originalSize.height;
                if (this.resizingLine) {
                    this.resizingLine.box = this.getBox();
                    this.resizingLine.setPosition();
                    this.resizingLine.scaleContent();
                }
            }, this)
        });
        
        $box.data('Box', this);
        $box.appendTo($('#seg-panel .img-container .zoom-container'));
        this.$element = $box;
        this.setPosition();
        
        // we need to keep references to be able to unbind it
        this.proxyUnselect = $.proxy(function(ev) {
            // click in the img doesn't unselect ?!
            if ($(ev.target).parents('#viewer').length) { return; }
            this.unselect();
        }, this);
        this.proxyKeyboard = $.proxy(this.keyboard, this);
        
        // select a new line
        if (this.pk === null) this.select();
        
        // avoid jquery-ui jumping
        $box.on('mousedown', function(ev) { ev.currentTarget.style.position = 'relative'; });
        $box.on('mouseup', function(ev) { ev.currentTarget.style.position = 'absolute'; });
        
        $box.click($.proxy(function(ev) {
            ev.stopPropagation();  // avoid bubbling to document that would trigger unselect
            this.select();
        }, this));
        
        $box.on('mouseover', $.proxy(function(ev) {
            this.showOverlay();
        }, this));
        $box.on('mouseleave', $.proxy(function(ev) {
            $('.overlay').hide();
        }, this));
        
        $('.close', this.$element).click($.proxy(function(ev) {
            ev.stopPropagation();
            this.delete();
        }, this));
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
    
    setPosition() {
        this.$element.css({
            'left': this.box[0] * this.ratio,
            'top': this.box[1] * this.ratio,
            'width': (this.box[2] - this.box[0]) * this.ratio,
            'height': (this.box[3] - this.box[1]) * this.ratio
        });
    }
    
    getBox() {
        var x1 = parseInt((this.$element.position().left) / zoom.scale / this.ratio);
        var y1 = parseInt((this.$element.position().top)  / zoom.scale / this.ratio);
        var x2 = parseInt(((this.$element.position().left) / zoom.scale + this.$element.width()) / this.ratio);
        var y2 = parseInt(((this.$element.position().top) / zoom.scale + this.$element.height()) / this.ratio);
        return [x1, y1, x2, y2];
    }
    showOverlay() {
        $('.overlay').css({
            left: this.box[0]*this.ratio + 'px',
            top: this.box[1]*this.ratio + 'px',
            width: (this.box[2] - this.box[0])*this.ratio + 'px',
            height: (this.box[3] - this.box[1])*this.ratio + 'px'
        }).show();
    }
    
    keyboard(ev) {
        if(!this.$element.is('.selected')) return;
        if (ev.keyCode == 46) {
            this.delete();
        }
        else if (ev.keyCode == 37) { this.$element.animate({'left': '-=1px'}); }
        else if (ev.keyCode == 38) { this.$element.animate({'top': '-=1px'}); }
        else if (ev.keyCode == 39) { this.$element.animate({'left': '+=1px'}); }
        else if (ev.keyCode == 40) { this.$element.animate({'top': '+=1px'}); }
    }
    select() {
        if (this.$element.is('.selected')) return;
        var previous = $('.box.selected');
        if (previous.length) { previous.data('Box').unselect(); }
        this.$element.addClass('selected');
        // this.$element.draggable('enable');
        // this.$element.resizable('enable');
        $(document).on('click', this.proxyUnselect);
        $(document).on('keyup', this.proxyKeyboard);
    }
    unselect() {
        $(document).off('keyup', this.proxykeyboard);
        $(document).off('click', this.proxyUnselect);
        this.$element.removeClass('selected');
        // this.$element.draggable('disable');
        // this.$element.resizable('disable');
        if (this.changed) {
            this.save();
        }
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
        if (this.pk !== null) {
            $.ajax({url: this.api.detail, type:'DELETE'});
        }
        $(document).unbind('keyup', this.proxykeyboard);
        $(document).off('click', this.proxyUnselect);
        this.$element.unbind();
        this.$element.remove();
        if (this.type == 'line') {
            var tl = $('#trans-box-line-'+this.pk).data('TranscriptionLine');
            if (tl) tl.delete();
        }
    }
}

class SegmentationPanel {
    constructor ($panel, opened) {
        this.$panel = $panel;
        this.opened = opened | false;
        this.seeBlocks = true;
        this.seeLines = true;
        this.$container = $('.img-container', this.$panel);
        this.boxes = [];
        
        $('#viewer-blocks', this.$panel).click($.proxy(function(ev) {
            $('#viewer-blocks').toggleClass('btn-primary').toggleClass('btn-secondary');
            this.seeBlocks = !this.seeBlocks;
            if (this.seeBlocks) $('.block-box').show();
            else $('.block-box').hide();
        }, this));
        $('#viewer-lines', this.$panel).click($.proxy(function(ev) {
            $('#viewer-lines').toggleClass('btn-primary').toggleClass('btn-secondary');
            this.seeLines = !this.seeLines;
            if (this.seeLines) {$('.line-box').show(); }
            else $('.line-box').hide();
        }, this));
        this.$container.on('dblclick', $.proxy(function(ev) {
            this.createBoxAtMousePos(ev, this.seeBlocks?'block':'line');
        }, this));
        this.$container.on('dblclick', '.block-box', $.proxy(function(ev) {
            ev.stopPropagation();
            this.createBoxAtMousePos(ev, 'line');
        }, this));
    }
    
    getRatio() {
        this.ratio = $('img', this.$container).width() / this.part.image.size[0];
    }
    
    createBoxAtMousePos(ev, mode) {
        var top_left_x = Math.max(0, ev.clientX - this.$container.offset().left) / zoom.scale / this.ratio;
        var top_left_y = Math.max(0, ev.clientY - this.$container.offset().top) / zoom.scale / this.ratio;
        var box = [
            parseInt(top_left_x),
            parseInt(top_left_y),
            parseInt(top_left_x + 200/zoom.scale/this.ratio),
            parseInt(top_left_y + 40/zoom.scale/this.ratio)
        ];
        var block = null;
        if ($(ev.target).is('.block-box')) {
            block = $(ev.target).data('Box').pk;
        };
        var box_ = new Box(mode, this.part, {
            order: mode=='line'?$('.line-box').length:$('.block-box').length,
            box: box,
            block: block}, this.ratio);
        box_.changed = true;  // makes sure it's saved
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
        this.boxes = [];
        $('.line-box, .block-box').remove();
        this.part = part;
        if (this.opened) this.open();
        if (this.part.image.thumbnails) {
            $('img', this.$container).attr('src', this.part.image.thumbnails.large);
        } else {
            $('img', this.$container).attr('src', this.part.image.uri);
        }
        this.getRatio();
        this.showBlocks();
        this.showLines();

        zoom.register(this.$container, true);
    }
    
    open() {
        this.opened = true;
        this.$panel.show();
        Cookies.set('seg-panel-open', true);
    }
    
    close() {
        this.opened = false;
        this.$panel.hide();
        Cookies.set('seg-panel-open', false);
    }
    
    toggle() {
        if (this.opened) this.close();
        else this.open();
    }
    
    reset() {
        if (this.opened) {
            this.getRatio();
            for (var i=0; i<this.boxes.length; i++) {
                this.boxes[i].setRatio(this.ratio);
                this.boxes[i].setPosition();
            }
        }
    }
}
