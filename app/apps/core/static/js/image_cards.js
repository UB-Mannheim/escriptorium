'use strict';

var API = {
    'document': '/api/documents/' + DOCUMENT_ID,
    'parts': '/api/documents/' + DOCUMENT_ID + '/parts/',
    'part': '/api/documents/' + DOCUMENT_ID + '/parts/{part_pk}/' 
};

Dropzone.autoDiscover = false;
var g_dragged = null;  // Note: chrome doesn't understand dataTransfer very well
var lastSelected = null;

class partCard {
    constructor(part) {
        this.pk = part.pk;
        this.name = part.name;
        this.title = part.title;
        this.typology = part.typology;
        this.image = part.image;
        this.bw_image = part.bw_image;
        this.workflow = part.workflow;
        this.progress = part.transcription_progress;
        this.locked = false;

        this.api = API.part.replace('{part_pk}', this.pk);
        
        var $new = $('.card', '#card-template').clone();
        this.$element = $new;
        this.domElement = this.$element.get(0);

        this.selectButton = $('.js-card-select-hdl', $new);
        this.deleteButton = $('.js-card-delete', $new);
        this.dropAfter = $('.js-drop', '#card-template').clone();
        
        // fill template
        $new.attr('id', $new.attr('id').replace('{pk}', this.pk));
        if (this.image.thumbnails != undefined) {
            $('img.card-img-top', $new).attr('data-src', this.image.thumbnails['card']);
        }
        $('img.card-img-top', $new).attr('title', this.title);

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

        // workflow icons & progress
        this.binarizedButton = $('.js-binarized', this.$element);
        this.segmentedButton = $('.js-segmented', this.$element);
        this.transcribeButton = $('.js-trans-progress', this.$element);
        this.progressBar = $('.progress-bar', this.transcribeButton);
        this.progressBar.css('width', this.progress + '%');
        this.progressBar.text(this.progress + '%');
        this.updateWorkflowIcons();
        var url = '/document/'+DOCUMENT_ID+'/part/'+this.pk+'/edit/';
        this.binarizedButton.click($.proxy(function(ev) {
            document.location.replace(url+'#bin');
        }, this));
        this.segmentedButton.click($.proxy(function(ev) {
            document.location.replace(url+'#seg');
        }, this));
        this.transcribeButton.click($.proxy(function(ev) {
            window.location.assign(url+'#trans');
        }, this));
        
        this.index = $('.card', '#cards-container').index(this.$element);
        // save a reference to this object in the card dom element
        $new.data('partCard', this);
        
        // add the image element to the lazy loader
        imageObserver.observe($('img', $new).get(0));
        
        this.defaultColor = this.$element.css('color');
        
        //************* events **************
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

        this.deleteButton.on('click', $.proxy(function(ev) {
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
                btn.removeClass('pending').removeClass('ongoing').removeClass('error').removeClass('done');
                btn.attr('title', btn.data('title'));
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
        }
    }

    remove() {
        this.dropAfter.remove();
        this.$element.remove();
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
    }
    unlock() {
        this.locked = false;
        this.$element.removeClass('locked');
        this.$element.attr('draggable', true);
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
            $.post(this.api + 'move/', {
                index: index
            }).done($.proxy(function(data){
                this.previousIndex = null;
            }, this)).fail($.proxy(function(data){
                this.moveTo(this.previousIndex, false);
                // show errors
                console.log('Something went wrong :(', data);
            }, this)).always($.proxy(function() {
                this.unlock();
            }, this));
        }
        this.index = index;
    }

    delete() {
        var posting = $.ajax({url:this.api, type: 'DELETE'})
            .done($.proxy(function(data) {
                this.remove();
            }, this))
            .fail($.proxy(function(xhr) {
                console.log("Couldn't delete part " + this.pk);
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
    $('#alerts-container').on('part:new', function(ev, data) {
        setTimeout(function() {  // really ugly: but avoid a race condition against dropzone
            var card = partCard.fromPk(data.id);
            if (!card) {
                var uri = API.part.replace('{part_pk}', data.id);
                $.get(uri, function(data) {
                    new partCard(data);
                });
            }
        }, 5000);
    });
    $('#alerts-container').on('part:delete', function(ev, data) {
        var card = partCard.fromPk(data.id);
        if (card) {
            card.remove();
        }
    });
    
    // create & configure dropzone
    var imageDropzone = new Dropzone('.dropzone', {
        paramName: "image",
        parallelUploads: 1  // ! important or the 'order' field gets duplicates
    });
    
    //************* New card creation **************
    imageDropzone.on("success", function(file, data) {
        var card = new partCard(data);
        card.domElement.scrollIntoView(false);
        // cleanup the dropzone if previews are pilling up
        if (imageDropzone.files.length > 7) {  // a bit arbitrary, depends on the screen but oh well
            for (var i=0; i < imageDropzone.files.length - 7; i++) {
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

    /* Keyboard Shortcuts */
    // $(document).keydown(function(e) {
    //     if(e.originalEvent.ctrlKey && e.originalEvent.key == 'z') {
    //         toggleZoom();
    //     }
    // });

    /* fetch the images and create the cards */
    var counter=0;
    var getNextParts = function(page) {
        var uri = API.parts + '?page=' + page;
        $.get(uri, function(data) {
            counter += data.results.length;            
            $('#loading-counter').html(counter+'/'+data.count);
            if (data.next) getNextParts(page+1);
            else { $('#loading-counter').parent().fadeOut(1000); }
            for (var i=0; i<data.results.length; i++) {
                new partCard(data.results[i]);
            }
        });
    };
    getNextParts(1);
});
