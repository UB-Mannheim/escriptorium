'use strict';

var API = {
    'document': '/api/documents/' + DOCUMENT_ID,
    'parts': '/api/documents/' + DOCUMENT_ID + '/parts/',
    'part': '/api/documents/' + DOCUMENT_ID + '/parts/{part_pk}/' 
};

Dropzone.autoDiscover = false;
var g_dragged = null;  // Note: chrome doesn't understand dataTransfer very well
var lastSelected = null;

function openWizard(proc) {        
    var selected_num = partCard.getSelectedPks().length;
        
    if(proc != 'import-iiif' && selected_num < 1) {
        alert('Select at least one image.');
        return;
    }
    // update selected count
    $('#selected-num', '#'+proc+'-wizard').text(selected_num);
    // can't send more than one binarized image at a time
    if (selected_num != 1) { $('#id_bw_image').attr('disabled', true); }
    else { $('#id_bw_image').attr('disabled', false); }
    
    // Reset the form
    $('.process-part-form', '#'+proc+'-wizard').get(0).reset();
    
    // initialize transcription field with user's last edited transcription
    let itrans = userProfile.get('initialTranscriptions');
    if (itrans && itrans[DOCUMENT_ID]) {
        $('#process-part-form-train #id_transcription').val(itrans[DOCUMENT_ID]);
    }
    
    $('#'+proc+'-wizard').modal('show');
}

class partCard {
    constructor(part) {
        this.pk = part.pk;
        this.name = part.name;
        this.title = part.title;
        this.typology = part.typology;
        this.image = part.image;
        this.filename = part.filename;
        this.bw_image = part.bw_image;
        this.workflow = part.workflow;
        this.task_ids = {};  // helps preventing card status race conditions
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
        this.updateThumbnail();
        $('img.card-img-top', $new).attr('title', this.title + '\n<' + this.filename +'>');

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
        this.editButton = $('.js-edit', this.$element);
        this.cancelTasksButton = $('.js-cancel', this.$element);
        this.convertIcon = $('.js-compressing', this.$element);
        this.binarizedButton = $('.js-binarized', this.$element);
        this.segmentedButton = $('.js-segmented', this.$element);
        this.transcribeButton = $('.js-trans-progress', this.$element);
        this.progressBar = $('.progress-bar', this.transcribeButton);
        this.progressBar.css('width', this.progress + '%');
        this.progressBar.text(this.progress + '%');
        this.updateWorkflowIcons();
        var url = '/document/'+DOCUMENT_ID+'/part/'+this.pk+'/edit/';
        this.editButton.click(function(ev) {
            document.location.replace(url);
        });
        this.cancelTasksButton.click($.proxy(function(ev) {
            this.cancelTasks();
        }, this));
        
        this.binarizedButton.click($.proxy(function(ev) {
            this.select();
            partCard.refreshSelectedCount();
            openWizard('binarize');
        }, this));
        this.segmentedButton.click($.proxy(function(ev) {
            this.select();
            partCard.refreshSelectedCount();
            openWizard('segment');
        }, this));
        this.transcribeButton.click($.proxy(function(ev) {
            this.select();
            partCard.refreshSelectedCount();
            openWizard('transcribe');
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
            partCard.refreshSelectedCount();
        }, this));

        this.deleteButton.on('click', $.proxy(function(ev) {
            if (!confirm("Do you really want to delete this image?")) { return; }
            this.delete();
            partCard.refreshSelectedCount();
        }, this));
        
        this.$element.on('dblclick', $.proxy(function(ev) {
            this.toggleSelect();
            partCard.refreshSelectedCount();
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
        return ((this.workflow['convert'] == 'pending' ||
                 this.workflow['binarize'] == 'pending' ||
                 this.workflow['segment'] == 'pending' ||
                 this.workflow['transcribe'] == 'pending') &&
                !this.working());
    }

    working() {
        return (this.workflow['convert'] == 'ongoing' ||
                this.workflow['binarize'] == 'ongoing' ||
                this.workflow['segment'] == 'ongoing' ||
                this.workflow['transcribe'] == 'ongoing');
    }
    
    isCancelable() {
        return (this.workflow['binarize'] == 'ongoing' ||
                this.workflow['segment'] == 'ongoing' ||
                this.workflow['transcribe'] == 'ongoing' ||
                this.workflow['binarize'] == 'pending' ||
                this.workflow['segment'] == 'pending' ||
                this.workflow['transcribe'] == 'pending');
    }

    updateThumbnail() {
        let uri, img = $('img.card-img-top', this.$element);
        
        if (this.image.thumbnails && this.image.thumbnails['card'] != undefined) {
            uri = this.image.thumbnails['card'];
        } else {
            uri = this.image.uri;
        }

        if (img.attr('src')) img.attr('src', uri);
        img.attr('data-src', uri);
    }
    
    updateWorkflowIcons() {
        var map = [
            ['convert', this.convertIcon],
            ['binarize', this.binarizedButton],
            ['segment', this.segmentedButton],
            ['transcribe', this.transcribeButton]];
        for (var i=0; i < map.length; i++) {
            var proc = map[i][0], btn = map[i][1];
            if (this.workflow[proc] == undefined) {
                btn.removeClass('pending').removeClass('ongoing').removeClass('error').removeClass('done');
                btn.attr('title', btn.data('title'));
            } else {
                btn.removeClass('pending').removeClass('ongoing').removeClass('error').removeClass('done');
                btn.addClass(this.workflow[proc]);
                btn.attr('title', btn.data('title') + ' ('+this.workflow[proc]+')');
            }            
        }
        
        if (this.inQueue() || this.working()) {
            this.lock();
        } else {
            this.unlock();
        }

        if (this.isCancelable()) {
            this.cancelTasksButton.show();
        } else {
            this.cancelTasksButton.hide();
        }
    }

    remove() {
        this.dropAfter.remove();
        this.$element.remove();
    }
    
    select(scroll=true) {
        if (this.locked) return;
        lastSelected = this;
        this.$element.addClass('bg-dark');
        this.$element.css({'color': 'white'});
        $('i', this.selectButton).removeClass('fa-square');
        $('i', this.selectButton).addClass('fa-check-square');
        if (scroll) this.$element.get(0).scrollIntoView();
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

    cancelTasks() {
        $.post(this.api + 'cancel/', {}).done($.proxy(function(data){
            this.workflow = data.workflow;
            this.updateWorkflowIcons();
        }, this)).fail($.proxy(function(data){console.log("Couldn't cancel the task.");}));
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
    static refreshSelectedCount() {
        $('#selected-counter').text(partCard.getSelectedPks().length+'/'+$('#cards-container .card').length).parent().show();
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
    var workflow_order = ['pending', 'ongoing', 'error', 'done'];
    $('#alerts-container').on('part:workflow', function(ev, data) {
        var card = partCard.fromPk(data.id);
        if (card) {
            if ((!data.task_id || card.task_ids[data.process] == data.task_id) &&
                workflow_order.indexOf(card.workflow[data.process]) > workflow_order.indexOf(data.status)) {
                return; // protection against race condition
            }
            card.workflow[data.process] = data.status;
            if (data.task_id) card.task_ids[data.process] = data.task_id;
            card.updateWorkflowIcons();

            
            // special case, done with thumbnails:
            if (data.process == 'generate_part_thumbnails' && data.status == 'done') {
                card.image.thumbnails = data.data;
                card.updateThumbnail();
            }
        } else {
            // we probably received the event before the card was created, retrigger ev in a sec
            setTimeout(function() {
                $('#alerts-container').trigger(ev, data);
            }, 100);
        }
    });
    $('#alerts-container').on('part:new', function(ev, data) {
        setTimeout(function() {  // really ugly: but avoid a race condition against dropzone
            var card = partCard.fromPk(data.id);
            if (!card) {
                var uri = API.part.replace('{part_pk}', data.id);
                $.get(uri, function(data) {
                    new partCard(data);
                    partCard.refreshSelectedCount();
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

    // Imports
    let $alertsContainer = $('#alerts-container');
    $alertsContainer.on('import:start', function(ev, data) {
        $('#import-counter').parent().addClass('ongoing');
        $('#import-selected').addClass('blink');
        $('#import-resume').hide();
    });
    $alertsContainer.on('import:progress', function(ev, data) {
        $('#import-counter').parent().addClass('ongoing');
        $('#import-selected').addClass('blink');
        if (data.progress) {
            $('#import-counter').text(data.progress+"/"+data.total);
        }
    });
    $alertsContainer.on('import:fail', function(ev, data) {
        $('#import-counter').text('failed');
        $('#import-selected').removeClass('blink');
        Alert.add('import-failed', "Import failed because '"+data.reason+"'", 'danger');
    });
    $alertsContainer.on('import:done', function(ev, data) {
        $('#import-counter').parent().removeClass('ongoing');
        $('#import-selected').removeClass('blink');
        Alert.add('import-done', "Import finished!", 'success');
    });
    $('#cancel-import').click(function(ev, data) {
        let url = API.document + '/cancel_import/';
        $.post(url, {})
            .done(function(data) {
                $('#import-counter').text('canceled');
                $('#import-counter').parent().removeClass('ongoing');
                $('#import-selected').removeClass('blink');
            })
            .fail(function(data) {
                console.log("Couldn't cancel import");
            });
    });
    
    // training
    var max_accuracy = 0;
    $alertsContainer.on('training:start', function(ev, data) {
        $('#train-selected').addClass('blink');
        $('#cancel-training').show();
    });
    $alertsContainer.on('training:gathering', function(ev, data) {
        $('#train-selected').addClass('blink');
        $('#cancel-training').show();
    });
    $alertsContainer.on('training:eval', function(ev, data) {
        $('#train-selected').addClass('blink');
        $('#cancel-training').show();
    });
    $alertsContainer.on('training:done', function(ev, data) {
        $('#train-selected').removeClass('blink');
        $('#cancel-training').hide();
    });
    $alertsContainer.on('training:error', function(ev, data) {
        $('#train-selected').removeClass('blink').addClass('btn-danger');
        $('#cancel-training').hide();
    });
    $('#cancel-training').click(function(ev, data) {
        let url = API.document + '/cancel_training/';
        $.post(url, {})
            .done(function(data) {
                $('#train-selected').removeClass('blink');
                $('#cancel-training').hide();
            })
            .fail(function(data) {
                console.log("Couldn't cancel training");
            });
    });
    
    // create & configure dropzone
    var imageDropzone = new Dropzone('.dropzone', {
        paramName: "image",
        timeout: 0,
        // chunking: true,
        // retryChunks: true,
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
            $(el).data('partCard').select(false);
        });
        partCard.refreshSelectedCount();
    });
    $('#unselect-all').click(function(ev) {
        var cards = partCard.getRange(0, $('#cards-container .card').length);
        cards.each(function(i, el) {
            $(el).data('partCard').unselect();
        });
        partCard.refreshSelectedCount();
    });
    
    $('.js-proc-selected').click(function(ev) {
        openWizard($(ev.target).data('proc'));
    });

    $('#process-part-form-binarize #id_threshold').on('input', function() {
        $(this).attr('title', this.value);
    });
    
    $('.process-part-form').submit(function(ev) {
        $('input[name=parts]', $form).val(JSON.stringify(partCard.getSelectedPks()));
        if ($(this).is('[data-proc="export"]')) return true;  // resume normal form behavior
        ev.preventDefault();
        var $form = $(ev.target);
        var proc = $form.data('proc');
        $('#'+proc+'-wizard').modal('hide');
        $.ajax({
            url : $form.attr('action'),
            type: $form.attr('method'),
            data : new FormData($form.get(0)),
            processData: false,
            contentType: false
        }).done(function(data) {
            if (DEBUG) console.log(proc+' process', data.status);
            if (proc == 'import-xml' || proc == 'import-iiif') {
                $('#import-counter').text('Queued.').show().parent().addClass('ongoing');;
            } else if (proc == 'train') {
                $('#train-selected').addClass('blink');
            }
        }).fail(function(xhr) {
            var data = xhr.responseJSON;
            if (data.status == 'error') { alert(data.error); }
            if (DEBUG) console.log(xhr);
        });
    });

    /* Select card if coming from edit page */
    var tabUrl = new URL(window.location);
    var select = tabUrl.searchParams.get('select');
    
    /* fetch the images and create the cards */
    var counter=0;
    var getNextParts = function(page) {
        var uri = API.parts + '?paginate_by=50&page=' + page;
        $.get(uri, function(data) {
            counter += data.results.length;            
            $('#loading-counter').html(counter+'/'+data.count);
            for (var i=0; i<data.results.length; i++) {
                var pc = new partCard(data.results[i]);
                if (select == pc.pk) pc.select();
            }
            if (data.next) {
                getNextParts(page+1);
            } else {
                $('#loading-counter').parent().hide();
                partCard.refreshSelectedCount();
            }
        });
    };
    getNextParts(1);
});
