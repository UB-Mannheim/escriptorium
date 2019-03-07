'use strict';
var editor;
var currentLine = null;
var my_zone = moment.tz.guess();

class TranscriptionLine {
    constructor (pk, order, box, transcriptions, imgWidth) {
        this.pk = pk;
        this.order = order;
        this.box = box;
        this.transcriptions = transcriptions;
        this.imgWidth = imgWidth;
        this.editing = false;
        
        var $el = $('<div id="trans-box-line-'+this.pk+'" class="trans-box"><span></span></div>');
        $el.data('TranscriptionLine', this);  // allow segmentation to target that box easily
        
        this.$element = $el;
        
        this.ratio = $('#part-img').width() / this.imgWidth;
        $el.css({
            left: this.box[0]*this.ratio + 'px',
            top: this.box[1]*this.ratio + 'px',
            width: (this.box[2] - this.box[0])*this.ratio  + 'px',
            height: (this.box[3] - this.box[1])*this.ratio + 'px',
            fontSize:  (this.box[3] - this.box[1])*this.ratio*0.7 + 'px',
            lineHeight: (this.box[3] - this.box[1])*this.ratio + 'px'
        });

        this.textContainer = $('span', $el).first();
        this.setText();
        this.textContainer.ready($.proxy(function(ev) {
            this.scaleContent();
        }, this));
        
        $('#part-trans').append($el);

        $el.on('mouseover', $.proxy(function(ev) {
            this.showOverlay();
        }, this));
        $el.on('mouseleave', $.proxy(function(ev) {
            if (!this.editing) $('#overlay').hide();
        }, this));
        $el.on('click', $.proxy(function(ev) {
            this.edit();
        }, this));
    }


    
    showOverlay() {
        $('#overlay').css({
            left: this.box[0]*this.ratio + 'px',
            top: this.box[1]*this.ratio + 'px',
            width: (this.box[2] - this.box[0])*this.ratio + 'px',
            height: (this.box[3] - this.box[1])*this.ratio + 'px'
        }).show();
    }

    getText() {
        var selectedTranscription = $('#document-transcriptions').val();
        if (this.transcriptions[selectedTranscription] !== undefined) {
            return this.transcriptions[selectedTranscription].content;
        } else {
            return '';
        }
    }
    setText() {
        this.textContainer.html(this.getText());
    }
    
    scaleContent() {
        var scaleX = Math.min(5, ((this.box[2] - this.box[0])*this.ratio) / this.textContainer.width());
        //var scaleY = this.textContainer.height() / ((this.box[3] - this.box[1])*this.ratio);
        this.textContainer.css({
            transform: 'scaleX('+scaleX+')'
        });
    }
    
    edit () {
        if (currentLine) currentLine.editing = false;
        this.editing = true;
        this.showOverlay();

        var content = this.getText();
        currentLine = this;
        // form hidden values
        var selectedTranscription = $('#document-transcriptions').val();
        $('#line-transcription-form [name=transcription]').val(selectedTranscription);
        $('#line-transcription-form [name=line]').val(this.pk);
        
        if (this.order == 0) { $("#trans-modal #prev-btn").attr('disabled', true); }
        else { $("#trans-modal #prev-btn").attr('disabled', false); }
        if (this.order == (lines.length-1)) { $("#trans-modal #next-btn").attr('disabled', true); }
        else { $("#trans-modal #next-btn").attr('disabled', false); }

        $('#trans-modal #trans-input .ql-editor').html(content); 
        
        // fill the history
        var $container = $('#trans-modal #history tbody');
        $container.empty();
        if (this.transcriptions[selectedTranscription] !== undefined) {
            $('#new-version-btn').prop('disabled', false);
            var versions = this.transcriptions[selectedTranscription].versions;
            if (versions && versions.length > 0) {
                $('#no-versions').hide();
                for (var i=versions.length-1; i>=0; i--) {
                    this.addVersionLine(versions[i]);
                }
            } else {
                $('#no-versions').show();
            }
        } else {
            $('#no-versions').show();
            $('#new-version-btn').prop('disabled', true);
        }

        // reset width to recalculate ratio
        $('#modal-img-container').css({width: '80%'});
        
        // need to show the modal before calculating sizes
        $('#trans-modal').modal('show');
        var originalWidth = (this.box[2] - this.box[0]);
        var originalHeight = (this.box[3] - this.box[1]);
        var boxWidth = $('#modal-img-container').width();
        var ratio = boxWidth / originalWidth;
        var MAX_HEIGHT = 200;
        if ((originalHeight * ratio) > MAX_HEIGHT) {
            ratio = ratio * originalHeight / MAX_HEIGHT;
        }
        $('#trans-modal #modal-img-container').animate({
            height: originalHeight * ratio + 'px',
            width: originalWidth * ratio + 'px'
        });

        // try to make the input match the image
        $('#trans-modal #trans-input .ql-editor').css({
            fontSize: originalHeight * ratio * 0.7 + 'px',
            lineHeight: originalHeight * ratio + 'px',
            height: originalHeight * ratio + 'px'
        });
        var $el = $('#trans-modal #trans-input .ql-editor');
        $el.css({width: 'initial', display: 'inline-block'}); // change to inline-block temporarily to calculate width
        if (content) {
            var scaleX = Math.min(5, originalWidth * ratio / $el.width());
            $el.css({
                transform: 'scaleX('+ scaleX +')',
                width: 100/scaleX + '%' // fit in the container
            });
        } else {
            $el.css({transform: 'none'});
        }
        $el.css({display: 'block'}); // revert to block to take the full space available
        
        $('#trans-modal #line-img').animate({
            left: '-'+this.box[0]*ratio+'px',
            top: '-'+this.box[1]*ratio+'px',
            width: this.imgWidth*ratio + 'px'
        }, 200);

        editor.focus();
    }

    addVersionLine(version) {
        var $container = $('#trans-modal #history tbody');
        var date = version.updated_at.replace('T', ' ');  // makes it moment.js compliant
        date = date.substring(0, 23) + date.substring(26);
        var $version = $('<tr id="rev-'+version.revision+'">'+
                         '<th class="js-version-content w-75">'+version.data.content+'</th>'+
                         '<td>'+version.author+'</td>'+
                         '<td class="js-version-date" data-date="'+date+'"></td>'+
                         '<td><button class="btn btn-sm btn-info js-pull-state" title="Load this state" data-rev="rev-'+version.revision+'">'+
                              '<i class="fas fa-file-upload"></i></button></td>'+
                         '</tr>');
        var $date = $('.js-version-date', $version);
        var mom = moment.tz($date.data('date'), my_zone);
        $date.html(mom.fromNow());
        $date.attr('title', "Last changed: "+mom.format('LLLL'));
        $container.prepend($version);
    }
    
    pushVersion() {
        var selectedTranscription = $('#document-transcriptions').val();
        var $form = $('#trans-modal #line-transcription-form');
        $.post($form.attr('action'), {
            transcription: selectedTranscription,
            line: this.pk,
            new_version: true
        }).done($.proxy(function(data) {
            if (data.status == 'ok') {
                $('#no-versions').hide();
                this.transcriptions[selectedTranscription].versions.splice(0, 0, data.transcription);
                this.addVersionLine(data.transcription);
            } else {
                alert(data.msg);
            }
        }, this)).fail(function(data) {
            console.log('damit.');
        });
    }
    
    save() {
        var selectedTranscription = $('#document-transcriptions').val();
        var new_content = $('#trans-modal #trans-input .ql-editor').html();
        if (this.transcriptions[selectedTranscription] != new_content) {
            var $form = $('#trans-modal #line-transcription-form');
            $.post($form.attr('action'), {
                transcription: selectedTranscription,
                line: this.pk,
                content: new_content
            })
                .done($.proxy(function(data){
                    if (this.transcriptions[selectedTranscription] === undefined) {
                        this.transcriptions[selectedTranscription] = {content: new_content, versions: []};
                    } else {
                        this.transcriptions[selectedTranscription].content = new_content;
                    }
                    this.textContainer.html(new_content);
                    this.textContainer.ready($.proxy(function(ev) {
                        this.scaleContent();
                    }, this));
                }, this))
                .fail(function(data) {
                    console.log('damit.');
                });
        }
    }
}

$(document).ready(function() {
    var $container = $('#img-container');
    WheelZoom($container, false, 1, 1);
    $container.get(0).addEventListener('wheelzoom.update', function(ev) {
        $('#part-trans').css({
            transform: 'translate('+ev.detail.translate.x+'px,'+ev.detail.translate.y+'px) scale('+ev.detail.scale+')'
        });
    });
    $('#document-transcriptions').change(function(ev) {
        for (var i=0; i<lines.length; i++) {
            lines[i].setText();
        }
    });
    $('#document-export button').click(function(ev) {
        ev.preventDefault();
        var selectedTranscription = $('#document-transcriptions').val();
        var href = $('a#document-export').attr('href');
        var new_href = href.replace(/(transcription\/)\d+(\/export)/,
                                    '$1'+selectedTranscription+'$2');
        window.open(new_href);
    });
    
    $("#trans-modal").draggable({
        handle: ".modal-header"
    });
    $("#trans-modal").on('hide.bs.modal', function(ev) {
        currentLine.editing = false;
        $('#overlay').hide();
    });
    $("#trans-modal #prev-btn").click(function(ev) {
        lines[currentLine.order-1].edit();
    });
    $("#trans-modal #next-btn").click(function(ev) {
        lines[currentLine.order+1].edit();
    });
    $('#trans-modal #new-version-btn').on('click', function (e, editor) {
        currentLine.pushVersion();
        $('#history').addClass('show');
    });
    $('#trans-modal #save-btn').on('click', function (e, editor) {
        currentLine.save();
        $('#trans-modal').modal('hide');
    });
    $('#trans-modal #save-continue-btn').on('click', function (e, editor) {
        currentLine.save();
        lines[currentLine.order+1].edit();
    });
    $('#trans-modal').on('click', '.js-pull-state', function(ev) {
        ev.preventDefault();
        var $tr = 'tr#'+$(ev.target).data('rev');
        $('#trans-modal #trans-input .ql-editor').html($('.js-version-content', $tr).html());
        
    });

    editor = new Quill('#trans-input', {
        theme: 'bubble',
        formats: ['bold', 'italic', 'strike', 'underline'],
        modules: {
            toolbar: ['bold', 'italic', 'strike', 'underline'],
            keyboard: { // disable enter key
                bindings: {
                    tab: false,
                    handle: {
                        key: 13,
                        handler: function() {
                            $('#trans-modal #save-continue-btn').click();
                        }
                    }
                }
            }
        }
    });
});
