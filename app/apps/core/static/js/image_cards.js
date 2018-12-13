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

class imageCard {
    constructor(part) {
        // part: pk, name, updateUrl, deleteUrl, sourceImg, thumbnail, bwImg, segmented, binarized
        this.pk = part.pk;
        this.name = part.name;
        this.thumbnail = part.thumbnail;  // TODO: use the form data to avoid a trip back
        this.sourceImg = part.sourceImg;
        this.bwImg = part.bwImg;
        this.updateUrl = part.updateUrl;
        this.deleteUrl = part.deleteUrl;
        this.workflow_state = part.workflow;
        
        var template = document.getElementById('card-template');
        var $new = $('.card', template).clone();
        this.$element = $new;
        this.domElement = this.$element.get(0);
        
        this.updateForm = $('.js-part-update-form', $new);
        this.deleteForm = $('.js-part-delete-form', $new);
        this.dropAfter = $('.js-drop', template).clone();
        
        $new.attr('id', $new.attr('id').replace('{pk}', this.pk));
        $('img.card-img-top', $new).attr('data-src', this.thumbnail);
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
        this.binarizedButton.click(this.showBW);
        this.segmentedButton.click(this.showSegmentation);
        
        this.index = $('.card', '#cards-container').index(this.$element);
        // save a reference to this object in the card dom element
        $new.data('imageCard', this);
        
        // add the image element to the lazy loader
        imageObserver.observe($('img', $new).get(0));
        
        //************* events **************
        this.updateForm.on('change', 'input', $.proxy(function(ev) {
            this.upload();
        }, this));
        
        this.deleteForm.on('submit', $.proxy(function(ev) {
            ev.preventDefault();
            if (!confirm("Are you sure?")) { return; }
            this.delete();
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
    }
    
    select() {
        this.$element.addClass('bg-dark');
        this.selected = true;
    }
    unselect() {
        this.$element.removeClass('bg-dark');
        this.selected = false;
    }
    toggleSelect() {
        if (this.selected) this.unselect();
        else this.select();
    }

    lock() {
        this.$element.css({opacity: 0.5});
        // TODO: lock on other clients via channels
        this.$element.attr('draggable', false);
    }
    unlock() {
        this.$element.css({opacity: ""});
        // TODO: unlock on other clients via channels
        this.$element.attr('draggable', true);
    }
    
    upload(data) {
        this.lock();
        // visual feedback for the background post
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
                if (data.index) { this.moveTo(this.previousIndex); }
                // show errors
                console.log('Something went wrong :(');
            }, this))
            .always($.proxy(function() {
                this.unlock();
            }, this));
    }
    
    moveTo(index) {
        // store the previous index in case of error
        this.previousIndex = this.index;
        var target = $('.js-drop')[index];
        this.$element.insertAfter(target);
        this.dropAfter.insertAfter(this.$element);  // drag the dropable zone with it
        if (this.previousIndex < index) { index--; }; // because the dragged card takes a room
        this.upload({index: index});
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

    showBW() {}
    showSegmentation() {}
}

$(document).ready(function() {
    //************* Card ordering *************
    $('#cards-container').on('dragover', '.js-drop', function(ev) {
        var index = $('.js-drop').index(ev.target);
        var elementId = ev.originalEvent.dataTransfer.getData("text/card-id");
        if (!elementId) { elementId = g_dragged; }  // for chrome
        var dragged_index = $('.card').index(document.getElementById(elementId));
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
        var card = $(dragged).data('imageCard');
        var index = $('.js-drop', '#cards-container').index(ev.target);
        card.moveTo(index);
    });

    // update workflow icons
    $('#alerts-container').on('part:workflow', function(ev, data) {
        var card = $('#image-card-'+data.id).data('imageCard');
        card.workflow_state = data.value;
        card.setWorkflowStates();
    });
    
    // create & configure dropzone
    var imageDropzone = new Dropzone('.dropzone', {
        paramName: "image",
        parallelUploads: 1  // ! important or the 'order' field gets duplicates
    });
    //************* New card creation **************
    imageDropzone.on("success", function(file, data) {
        if (data.status === 'ok') {
            var card = new imageCard(data.part);
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

    $('.js-segment').click(function(ev) {
        var $link = $(ev.target), box;
        $('.line-box', '#segment-viewer').remove(); // cleanup
        $.get($link.data('lines-url'), function(data) {
            $('#segment-viewer img').attr('src', $link.data('src-img'));
            for (i=0; i<data.length; i++) {
                box = $('#box-tplt').clone();
                box.css('left', data[i][0]);
                box.css('top', data[i][1]);
                box.css('width', data[i][2] - data[i][0]);
                box.css('height', data[i][3] - data[i][1]);
                box.attr('id', '');
                box.show();
                box.appendTo('#segment-viewer');
            }
        });
    });
});
