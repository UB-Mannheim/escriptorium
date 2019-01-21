'use strict';

Dropzone.autoDiscover = false;
var g_dragged = null;  // Note: chrome doesn't understand dataTransfer very well
var wz, lastSelected = null, viewing=null;

class partCard {
    constructor(part) {
        this.pk = part.pk;
        this.name = part.name;
        this.title = part.title;
        this.typology = part.typology;
        this.thumbnailUrl = part.thumbnailUrl;  // TODO: use the form data to avoid a trip back
        this.image = part.image;
        this.bwImgUrl = part.bwImgUrl;
        this.updateUrl = part.updateUrl;
        this.deleteUrl = part.deleteUrl;
        this.transcripionUrl = part.transcriptionUrl;
        this.partUrl = part.partUrl;
        this.workflow = part.workflow;
        this.progress = part.progress;
        this.locked = false;
        this.lines = [];
        
        var template = document.getElementById('card-template');
        var $new = $('.card', template).clone();
        this.$element = $new;
        this.domElement = this.$element.get(0);

        this.selectButton = $('.js-card-select-hdl', $new);
        this.updateForm = $('.js-part-update-form', $new);
        this.deleteForm = $('.js-part-delete-form', $new);
        this.dropAfter = $('.js-drop', template).clone();

        // fill template
        $new.attr('id', $new.attr('id').replace('{pk}', this.pk));
        $('img.card-img-top', $new).attr('data-src', this.thumbnailUrl);
        $('img.card-img-top', $new).attr('title', this.title);
        this.updateForm.attr('action', this.updateUrl);
        $('input[name=name]', this.updateForm).attr('value', this.name);
        $('select[name=typology] option[value='+this.typology+']', this.updateForm).attr('selected', 'true');
        this.deleteForm.attr('action', this.deleteUrl);

        $new.attr('draggable', true);
        $('img', $new).attr('draggable', false);
        $('img', $new).attr('selectable', false);
        // disable dragging when over input because firefox gets confused
        $('input', this.$element).on('mouseover', $.proxy(function(ev) {
            this.$element.attr('draggable', false);
        }, this)).on('mouseout', $.proxy(function(ev) {
            this.$element.attr('draggable', true);
        }, this));
        
        // add to the dom
        $('#cards-container').append($new);
        $('#cards-container').append(this.dropAfter);
        this.domElement.scrollIntoView(false);

        // workflow icons & progress
        this.binarizedButton = $('.js-binarized', this.$element);
        this.segmentedButton = $('.js-segmented', this.$element);
        this.transcribeButton = $('.js-trans-progress', this.$element);
        this.progressBar = $('.progress-bar', this.transcribeButton);
        this.progressBar.css('width', this.progress + '%');
        this.progressBar.text(this.progress + '%');
        this.updateWorkflowIcons();
        this.binarizedButton.click($.proxy(function(ev) { this.showBW(); }, this));
        this.segmentedButton.click($.proxy(function(ev) { this.showSegmentation(); }, this));
        this.transcribeButton.click($.proxy(function(ev) {
            if (this.workflow['transcribe'] == 'done') {
                window.location.assign(this.transcripionUrl);
            }
        }, this));
        
        this.index = $('.card', '#cards-container').index(this.$element);
        // save a reference to this object in the card dom element
        $new.data('partCard', this);
        
        // add the image element to the lazy loader
        imageObserver.observe($('img', $new).get(0));
        
        this.defaultColor = this.$element.css('color');
        
        //************* events **************
        $('.js-edit', this.$element).click($.proxy(function(ev) { this.updateForm.toggle(); }, this));
        this.updateForm.on('change', 'input,select', $.proxy(function(ev) {
            this.upload();
        }, this));

        this.selectButton.on('click', $.proxy(function(ev) {
            if (ev.shiftKey) {
                if (lastSelected) {
                    var cards = partCard.getRange(lastSelected.index, this.index);
                    cards.each(function(i, el) {
                        $(el).data('partCard').select();
                    });
                }
            } else {
                this.toggleSelect();
            }
        }, this));
        
        this.deleteForm.on('submit', $.proxy(function(ev) {
            ev.preventDefault();
            if (!confirm("Do you really want to delete this image?")) { return; }
            this.delete();
        }, this));

        this.$element.on('dblclick', $.proxy(function(ev) {
            this.toggleSelect();
        }, this));
        
        // drag'n'drop
        this.$element.on('dragstart', $.proxy(function(ev) {
            if (this.locked) return;
            ev.originalEvent.dataTransfer.setData("text/card-id", ev.target.id);
            g_dragged = ev.target.id;  // chrome gets confused with dataTransfer, so we use a global
            $('.js-drop').addClass('drop-target');
        }, this));
        this.$element.on('dragend', $.proxy(function(ev) {
            $('.js-drop').removeClass('drop-target');
        }, this));        
    }

    inQueue() {
        return ((this.workflow['binarize'] == 'pending' ||
                 this.workflow['segment'] == 'pending' ||
                 this.workflow['transcribe'] == 'pending') &&
                !this.working());
    }

    working() {
        return (this.workflow['binarize'] == 'ongoing' ||
                this.workflow['segment'] == 'ongoing' ||
                this.workflow['transcribe'] == 'ongoing');
    }
    
    updateWorkflowIcons() {
        var map = [['binarize', this.binarizedButton],
                   ['segment', this.segmentedButton],
                   ['transcribe', this.transcribeButton]];
        for (var i=0; i < map.length; i++) {
            var proc = map[i][0], btn = map[i][1];
            if (this.workflow[proc] == undefined) {
                btn.hide();
            } else {
                btn.removeClass('pending').removeClass('ongoing').removeClass('error').removeClass('done');
                btn.addClass(this.workflow[proc]).show();
                btn.attr('title', btn.data('title') + ' ('+this.workflow[proc]+')');
            }            
        }
        
        if (this.workflow['binarize'] == 'ongoing' ||
            this.workflow['segment'] == 'ongoing' ||
            this.workflow['transcribe'] == 'ongoing') {
            this.lock();
        }
        
        if (this.inQueue() || this.working()) {
            this.lock();
        } else {
            this.unlock();
        }
        
        if (this.workflow['transcribe'] == 'done') {
            $('#nav-trans-tab').removeClass('disabled');
            // this.progressBar.parent().css('display', 'inline-block');
        }
    }
    
    select() {
        if (this.locked) return;
        lastSelected = this;
        this.$element.addClass('bg-dark');
        this.$element.css({'color': 'white'});
        $('i', this.selectButton).removeClass('fa-square');
        $('i', this.selectButton).addClass('fa-check-square');
        this.selected = true;
    }
    unselect() {
        lastSelected = null;
        this.$element.removeClass('bg-dark');
        this.$element.css({'color': this.defaultColor});
        $('i', this.selectButton).removeClass('fa-check-square');
        $('i', this.selectButton).addClass('fa-square');
        this.selected = false;
    }
    toggleSelect() {
        if (this.selected) this.unselect();
        else this.select();
    }

    lock() {
        this.locked = true;
        this.$element.addClass('locked');
        this.$element.attr('draggable', false);
        // $('input', this.updateForm).get(0).disabled = true;
    }
    unlock() {
        this.locked = false;
        this.$element.removeClass('locked');
        this.$element.attr('draggable', true);
        // $('input', this.updateForm).get(0).disabled = false;
    }
    
    upload(data) {
        this.lock();
        if (data === undefined) { data = {}; }
        var post = {};
        this.updateForm.serializeArray().map(function(x){post[x.name] = x.value;});
        post = Object.assign({}, post, data);
        var url = this.updateForm.attr("action");
        var posting = $.post(url, post)
            .done($.proxy(function(data) {
                // we moved it optimistically
                this.previousIndex = null;
            }, this))
            .fail($.proxy(function(xhr) {
                // fly it back
                if (data.index) { this.moveTo(this.previousIndex, false); }
                // show errors
                console.log('Something went wrong :(');
            }, this))
            .always($.proxy(function() {
                this.unlock();
            }, this));
    }
    
    moveTo(index, upload) {
        if (upload === undefined) upload = true;
        // store the previous index in case of error
        this.previousIndex = this.index;
        var target = $('#cards-container .js-drop')[index];
        this.$element.insertAfter(target);
        this.dropAfter.insertAfter(this.$element);  // drag the dropable zone with it
        if (this.previousIndex < index) { index--; }; // because the dragged card takes a room
        if (upload) {
            this.upload({index: index});
        }
        this.index = index;
    }
    
    delete() {
        var posting = $.post(this.deleteForm.attr('action'),
                             this.deleteForm.serialize())
            .done($.proxy(function(data) {
                this.dropAfter.remove();
                this.$element.remove();
            }, this))
            .fail($.proxy(function(xhr) {
                console.log("damit.");
            }, this));
    }

    showBW() {
        // Note: have to recreate an image because webkit never really delete the boxes otherwise
        var $viewer = $('#viewer');
        $viewer.empty();
        if (!this.bwImgUrl) {
            $.get(this.partUrl, $.proxy(function(data) {
                this.lines = data.lines;
                this.bwImgUrl = data.bwImgUrl;
                this.image = data.image;
                var $img = $('<img id="viewer-img" width="100%" src="'+this.bwImgUrl+'"/>');
                $viewer.append($img);
            }, this));
        } else {
            var $img = $('<img id="viewer-img" width="100%" src="'+this.bwImgUrl+'"/>');
            $viewer.append($img);
        }
        viewing = {index: this.index, mode:'bw'};
        if (this.index == 0) { $('#viewer-prev').attr('disabled', true); }
        else { $('#viewer-prev').attr('disabled', false); }
        if (this.index >= $('#cards-container .card').length-1) { $('#viewer-next').attr('disabled', true); }
        else { $('#viewer-next').attr('disabled', false); }
        $('#viewer-create-line').hide();
        $('#viewer-binarization').hide();
        $('#viewer-segmentation').show();
        
        $('#viewer-img').on('load', $.proxy(function(ev) {
            $('#viewer-container').trigger('wheelzoom.refresh');
        }, this));
    }

    showLines(ratio) {
        var line;
        for (var i=0; i<this.lines.length; i++) {
            line = this.lines[i];
            new lineBox(this, line, ratio);
        }
    }
    showSegmentation() {
        var $img, ratio;
        
        if (this.lines.length) {
            update_(this);
        } else {
            $.get(this.partUrl, $.proxy(function(data) {
                this.lines = data.lines;
                this.bwImgUrl = data.bwImgUrl;
                this.image = data.image;
                update_(this);
            }, this));
        }
        
        function update_(this_) {
            var $viewer = $('#viewer');
            $viewer.empty();
            $img = $('<img id="viewer-img" width="100%" src="'+this_.image.url+'"/>');
            $viewer.append($img);
            
            viewing = {index: this_.index, mode:'seg'};
            if (this_.index == 0) { $('#viewer-prev').attr('disabled', true); }
            else { $('#viewer-prev').attr('disabled', false); }
            if (this_.index >= $('#cards-container .card').length-1) { $('#viewer-next').attr('disabled', true); }
            else { $('#viewer-next').attr('disabled', false); }
            $('#viewer-create-line').show();
            $('#viewer-binarization').show();
            $('#viewer-segmentation').hide();
            
            $('#viewer-img').on('load', $.proxy(function(ev) {
                $('#viewer-container').trigger('wheelzoom.refresh');
                ratio = $('#viewer-img').width() / this_.image.width;
                this_.showLines(ratio);
                // create a new line
                $('#viewer-img').on('dblclick', function(ev) {
                    var box = [
                        Math.max(0, ev.pageX - $img.offset().left -30) / ratio / wz.scale,
                        Math.max(0, ev.pageY - $img.offset().top -20) / ratio / wz.scale,
                        Math.min($img.width() * ratio * wz.scale, ev.pageX - $img.offset().left +30) / ratio / wz.scale,
                        Math.min($img.height() * ratio * wz.scale, ev.pageY - $img.offset().top +20) / ratio / wz.scale
                    ];
                    var box_ = new lineBox(this_, {pk: null, box: box}, ratio);
                });
            }, this_));
        }
    }

    static fromPk(pk) {
        return $('#image-card-'+pk).data('partCard');
    }
    static getRange(from_, to_) {
        var from, to;
        if (from_ < to_) from = from_, to = to_;
        else from = to_, to = from_;
        return $('#cards-container .card').slice(from, to+1);
    }
    static getSelectedPks() {
        var pks = [];
        $('#cards-container .card').each(function(i, el) {
            var ic = $(el).data('partCard');
            if (ic.selected) {
                pks.push(ic.pk);
            }
        });
        return pks;
    }
}

class lineBox {
    constructor(part, line, imgRatio) {
        this.part = part;
        this.pk = line.pk;
        this.imgRatio = imgRatio;
        this.changed = false;
        this.click = {x: null, y:null};
        this.originalWidth = (line.box[2] - line.box[0]) * imgRatio;
        var $box = $('<div class="line-box"> <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>');
        $box.css({'left': line.box[0] * imgRatio,
                  'top': line.box[1] * imgRatio,
                  'width': (line.box[2] - line.box[0]) * imgRatio,
                  'height': (line.box[3] - line.box[1]) * imgRatio});
        $box.draggable({
            disabled: true,
            containment: 'parent',
            cursor: "grab",
            stop: $.proxy(function(ev) {
                this.changed = true;
                $('#viewer-container').trigger('wheelzoom.enable');
            }, this),
            // this is necessary because WheelZoom make it jquery-ui drag jump around
            start: $.proxy(function(event) {
                this.click.x = event.clientX;
                this.click.y = event.clientY;
                $('#viewer-container').trigger('wheelzoom.disable');
            }, this),
            drag: $.proxy(function(event, ui) {
                var original = ui.originalPosition;
                ui.position = {
                    left: (event.clientX - this.click.x + original.left) / wz.scale,
                    top:  (event.clientY - this.click.y + original.top ) / wz.scale
                };
            }, this)
        });
        $box.resizable({
            disabled: true,
            stop: $.proxy(function(ev) {
                this.changed = true;
                $('#viewer-container').trigger('wheelzoom.enable');
            }, this),
            start: function(ev) {
                $('#viewer-container').trigger('wheelzoom.disable');
            }
        });
        
        $box.data('lineBox', this);
        $box.appendTo($('#viewer'));
        this.$element = $box;
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

        $('.close', this.$element).click($.proxy(function(ev) {
            ev.stopPropagation();
            this.delete();
        }, this));
    }

    getBox() {
        var x1 = parseInt((this.$element.position().left) / wz.scale / this.imgRatio);
        var y1 = parseInt((this.$element.position().top) / wz.scale / this.imgRatio);
        var x2 = parseInt(((this.$element.position().left) / wz.scale + this.$element.width()) / this.imgRatio);
        var y2 = parseInt(((this.$element.position().top) / wz.scale + this.$element.height()) / this.imgRatio);
        return [x1, y1, x2, y2];
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
        var previous = $('.line-box.selected');
        if (previous.length) { previous.data('lineBox').unselect(); }
        this.$element.addClass('selected');
        this.$element.draggable('enable');
        this.$element.resizable('enable');
        $(document).on('click', this.proxyUnselect);
        $(document).on('keyup', this.proxyKeyboard);
    }
    unselect() {
        $(document).off('keyup', this.proxykeyboard);
        $(document).off('click', this.proxyUnselect);
        this.$element.removeClass('selected');
        this.$element.draggable('disable');
        this.$element.resizable('disable');
        if (this.changed) {
            this.part.upload({lines: JSON.stringify([{pk: this.pk, box: this.getBox()}])});
            this.changed = false;
        }
    }
    delete() {
        if (!confirm("Do you really want to delete this line?")) { return; }
        if (this.pk !== null) { 
            this.part.upload({lines: JSON.stringify([{pk: this.pk, delete: true}])});
        }
        $(document).unbind('keyup', this.proxykeyboard);
        $(document).off('click', this.proxyUnselect);
        this.$element.unbind();
        this.$element.remove();
    }
}

$(document).ready(function() {
    //************* Card ordering *************
    $('#cards-container').on('dragover', '.js-drop', function(ev) {
        var index = $('#cards-container .js-drop').index(ev.target);
        var elementId = ev.originalEvent.dataTransfer.getData("text/card-id");
        if (!elementId && g_dragged != null) { elementId = g_dragged; }  // for chrome
        var dragged_index = $('#cards-container .card').index(document.getElementById(elementId));
        var isCard = ev.originalEvent.dataTransfer.types.indexOf("text/card-id") != -1;
        if (isCard && index != dragged_index && index != dragged_index + 1) {
            $(ev.target).addClass('drop-accept');
            ev.preventDefault();
        }
    });
    
    $('#cards-container').on('dragleave','.js-drop', function(ev) {
        ev.preventDefault();
        $(ev.target).removeClass('drop-accept');
    });
    
    $('#cards-container').on('drop', '.js-drop', function(ev) {
        ev.preventDefault();
        $(ev.target).removeClass('drop-accept');
        var elementId = ev.originalEvent.dataTransfer.getData("text/card-id");
        if (!elementId) { elementId = g_dragged; }  // for chrome
        var dragged = document.getElementById(elementId);
        var card = $(dragged).data('partCard');
        var index = $('#cards-container .js-drop').index(ev.target);
        card.moveTo(index);
        g_dragged = null;
    });

    // update workflow icons, send by notification through web socket
    $('#alerts-container').on('part:workflow', function(ev, data) {
        var card = partCard.fromPk(data.id);
        if (card) {
            card.workflow[data.process] = data.status;
            card.updateWorkflowIcons();
        } else {
            // we probably received the event before the card was created, retrigger ev in a sec
            setTimeout(function() {
                $('#alerts-container').trigger(ev, data);
            }, 1000);
        }
    });
    
    // create & configure dropzone
    var imageDropzone = new Dropzone('.dropzone', {
        paramName: "image",
        parallelUploads: 1  // ! important or the 'order' field gets duplicates
    });
    //************* New card creation **************
    imageDropzone.on("success", function(file, data) {
        if (data.status === 'ok') {
            var card = new partCard(data.part);
        }
        // cleanup the dropzone if previews are pilling up
        if (imageDropzone.files.length > 7) {  // a bit arbitrary, depends on the screen but oh well
            for (i=0; i < imageDropzone.files.length - 7; i++) {
                if (imageDropzone.files[i].status == "success") {
                    imageDropzone.removeFile(imageDropzone.files[i]);
                }
            }
        }
    });
    
    // processor buttons
    $('#select-all').click(function(ev) {
        var cards = partCard.getRange(0, $('#cards-container .card').length);
        cards.each(function(i, el) {
            $(el).data('partCard').select();
        });
    });
    $('#unselect-all').click(function(ev) {
        var cards = partCard.getRange(0, $('#cards-container .card').length);
        cards.each(function(i, el) {
            $(el).data('partCard').unselect();
        });
    });
    
    $('.js-proc-selected').click(function(ev) {
        var proc = $(ev.target).data('proc');
        var selected_num = partCard.getSelectedPks().length;
        if(selected_num > 0) {
            // update selected count
            $('#selected-num', '#'+proc+'-wizard').text(selected_num);
            if (selected_num != 1) { $('#id_bw_image').attr('disabled', true); }
            else { $('#id_bw_image').attr('disabled', false); }
            
            // Reset the form
            $('.process-part-form', '#'+proc+'-wizard').get(0).reset();
            
            $('#'+proc+'-wizard').modal('show');
        } else {
            alert('Select at least one image.');
        }
    });
    $('.process-part-form').submit(function(ev) {
        ev.preventDefault();
        var $form = $(ev.target);
        var proc = $form.data('proc');
        $('input[name=parts]', $form).val(JSON.stringify(partCard.getSelectedPks()));
        $('#'+proc+'-wizard').modal('hide');
        console.log($form, $form.get(0));

        $.ajax({
            url : $form.attr('action'),
            type: "POST",
            data : new FormData($form.get(0)),
            processData: false,
            contentType: false
        }).done(function(data) {
            console.log(proc+' process', data.status);
        }).fail(function(xhr) {
            var data = xhr.responseJSON;
            if (data.status == 'error') { alert(data.error); }
        });
    });
    
    // zoom
    wz = WheelZoom($('#viewer-container'), 1);

    // viewer buttons
    $('#viewer-prev').click(function(ev) {
        if (viewing && viewing.index > 0) {
            var card = $('#cards-container .card:eq('+(viewing.index-1)+')').data('partCard');
            if (viewing.mode == 'bw') { card.showBW(); }
            else if(viewing.mode == 'seg') { card.showSegmentation(); }
        }
    });
    $('#viewer-next').click(function(ev) {
        if (viewing && viewing.index < $('#cards-container .card').length) {
            var card = $('#cards-container .card:nth('+(viewing.index+1)+')').data('partCard');
            if (viewing.mode == 'bw') { card.showBW(); }
            else if(viewing.mode == 'seg') { card.showSegmentation(); }
        }
    });
    $('#viewer-reset').click(function(ev) {
        $('#viewer-container').trigger('wheelzoom.reset');
    });
    $('#viewer-binarization').click(function(ev) {
        var card = $('#cards-container .card:eq('+(viewing.index)+')').data('partCard');
        if (viewing.mode != 'bw') { card.showBW(); }
    });
    $('#viewer-segmentation').click(function(ev) {
        var card = $('#cards-container .card:eq('+(viewing.index)+')').data('partCard');
        if(viewing.mode != 'seg') { card.showSegmentation(); }
    });
    $('#viewer-create-line').click(function(ev) {
        var card = $('#cards-container .card:eq('+(viewing.index)+')').data('partCard');
        var lb = new lineBox(card, {pk: null, box: [50, 100, 400, 200]}, $('#viewer-img').width() / card.image.width);
        lb.select();
    });
});
