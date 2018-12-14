'use strict';
/**** Image cards drag n drop stuff ****/
/* TODOList
* icons bw, segmented (linked to messages)
* select
* api for hooks with advanced form
* locking (can't run another job while one is already running)
*/

Dropzone.autoDiscover = false;
var g_dragged;  // Note: chrome doesn't understand dataTransfer very well
var viewer, lastSelected = null;

class partCard {
    constructor(part) {
        this.pk = part.pk;
        this.name = part.name;
        this.thumbnailUrl = part.thumbnailUrl;  // TODO: use the form data to avoid a trip back
        this.sourceImg = part.sourceImg;
        this.bwImgUrl = part.bwImgUrl;
        this.updateUrl = part.updateUrl;
        this.deleteUrl = part.deleteUrl;
        this.partUrl = part.partUrl;
        this.workflow_state = part.workflow;
        this.locked = false;
        this.lines = null;
        
        var template = document.getElementById('card-template');
        var $new = $('.card', template).clone();
        this.$element = $new;
        this.domElement = this.$element.get(0);

        this.selectButton = $('.js-card-select-hdl', $new);
        this.updateForm = $('.js-part-update-form', $new);
        this.deleteForm = $('.js-part-delete-form', $new);
        this.dropAfter = $('.js-drop', template).clone();
        
        $new.attr('id', $new.attr('id').replace('{pk}', this.pk));
        $('img.card-img-top', $new).attr('data-src', this.thumbnailUrl);
        this.updateForm.attr('action', this.updateUrl);
        $('input[name=name]', this.updateForm).attr('value', this.name);
        this.deleteForm.attr('action', this.deleteUrl);

        $new.attr('draggable', true);
        $('img', $new).attr('draggable', false);
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
        this.setWorkflowStates();
        this.binarizedButton.click($.proxy(function(ev) { this.showBW(); }, this));
        this.segmentedButton.click($.proxy(function(ev) { this.showSegmentation(); }, this));
        
        this.index = $('.card', '#cards-container').index(this.$element);
        // save a reference to this object in the card dom element
        $new.data('partCard', this);
        
        // add the image element to the lazy loader
        imageObserver.observe($('img', $new).get(0));

        this.defaultColor = this.$element.css('color');
        
        //************* events **************
        this.updateForm.on('change', 'input', $.proxy(function(ev) {
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
            if (!confirm("Are you sure?")) { return; }
            this.delete();
        }, this));

        this.$element.on('dblclick', $.proxy(function(ev) {
            this.toggleSelect();
        }, this));
        
        // drag'n'drop
        this.$element.on('dragstart', $.proxy(function(ev) {
            ev.originalEvent.dataTransfer.setData("text/card-id", ev.target.id);
            g_dragged = ev.target.id;  // chrome gets confused with dataTransfer, so we use a global
            $('.js-drop').addClass('drop-target');
        }, this));
        this.$element.on('dragend', $.proxy(function(ev) {
            $('.js-drop').removeClass('drop-target');
        }, this));        
    }

    setWorkflowStates() {
        this.binarizing = this.workflow_state == 1; // meh
        this.binarized = this.workflow_state >= 2;
        this.segmenting = this.workflow_state == 3;
        this.segmented = this.workflow_state >= 4;
        if (this.binarizing) { this.binarizedButton.addClass('ongoing').show(); }
        if (this.binarized) { this.binarizedButton.removeClass('ongoing').addClass('done').show(); }
        if (this.segmenting) { this.segmentedButton.addClass('ongoing').show(); }
        if (this.segmented) { this.segmentedButton.removeClass('ongoing').addClass('done').show(); }
        if (this.binarizing || this.segmenting) {
            this.bwImgUrl = null;
            this.lines = null;
            this.lock();
        } else {
            this.unlock();
        }
    }
    
    select() {
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
        this.$element.css({opacity: 0.5});
        this.$element.attr('draggable', false);
        // $('input', this.updateForm).get(0).disabled = true;
    }
    unlock() {
        this.locked = false;
        this.$element.css({opacity: ""});
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
                this.bwImgUrl = data.bwImgUrl;
                var $img = $('<img id="viewer-img" width="100%" src="'+this.bwImgUrl+'"/>');
                $viewer.append($img);
            }, this));
        } else {
            var $img = $('<img id="viewer-img" width="100%" src="'+this.bwImgUrl+'"/>');
            $viewer.append($img);
        }
    }

    showLines() {
        var box, line, ratio = $('#viewer-img').width() / this.sourceImg.width;        
        for (var i=0; i<this.lines.length; i++) {
            line = this.lines[i];
            box = $('<div class="line-box"></div>');
            box.css({'left': line[0] * ratio,
                     'top': line[1] * ratio,
                     'width': (line[2] - line[0]) * ratio,
                     'height': (line[3] - line[1]) * ratio});
            box.removeAttr('id');
            box.show();
            box.appendTo($('#viewer'));
        }
    }
    showSegmentation() {
        var $viewer = $('#viewer');
        $viewer.empty();
        var $img = $('<img id="viewer-img" width="100%" src="'+this.sourceImg.url+'"/>');
        $viewer.append($img);
        $('#viewer-img').on('load', $.proxy(function(ev) {
            if (this.lines) {
                this.showLines();
            } else {
                $.get(this.partUrl, $.proxy(function(data) {
                    this.lines = data.lines;
                    this.showLines();
                }, this));
            }
        }, this));
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

$(document).ready(function() {
    //************* Card ordering *************
    $('#cards-container').on('dragover', '.js-drop', function(ev) {
        var index = $('#cards-container .js-drop').index(ev.target);
        var elementId = ev.originalEvent.dataTransfer.getData("text/card-id");
        if (!elementId) { elementId = g_dragged; }  // for chrome
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
    });

    // update workflow icons
    $('#alerts-container').on('part:workflow', function(ev, data) {
        var card = partCard.fromPk(data.id);
        card.workflow_state = data.value;
        card.setWorkflowStates();
    });
    
    // create & configure dropzone
    var imageDropzone = new Dropzone('.dropzone', {
        paramName: "image",
        parallelUploads: 1  // ! important or the 'order' field gets duplicates
    });
    imageDropzone.on("sending", function(file, xhr, formData) {
        formData.append("auto_process", $('input[name=auto_process]', '#dropzone').get(0).checked);
        formData.append("text_direction", $('select[name=text_direction]', '#dropzone').val());
        formData.append("typology", $('select[name=typology]', '#dropzone').val());
        // formData.append("binarizer", $('select[name=binarizer]', '#dropzone').val());
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
    $('#binarize-selected').click(function(ev) {
        $.post(processDocumentPartsUrl, {
            'parts': partCard.getSelectedPks(),
            'process': 'binarize'
        }).done(function(data) {
            console.log('binarization process', data.status);
        }).fail(function(xhr) {
            console.log('Something went wrong :(');
        });
    });
    $('#segment-selected').click(function(ev) {
        // $('select[name=text_direction]', '#dropzone').val()
        $.post(processDocumentPartsUrl, {
            'parts': partCard.getSelectedPks(),
            'process': 'segment'
        }).done(function(data) {
            console.log('binarization process', data.status);
        }).fail(function(xhr) {
            console.log('Something went wrong :(');
        });
    });
});
