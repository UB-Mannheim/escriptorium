'use strict';
var lines = [], currentLine = null;

class TranscriptionLine {
    constructor (pk, order, box, transcriptions, imgWidth) {
        this.pk = pk;
        this.order = order;
        this.box = box;
        this.transcriptions = transcriptions;
        this.imgWidth = imgWidth;

        var $el = $('<div class="trans-box"><span></span></div>');
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
        this.textContainer.html(this.getText());
        this.textContainer.ready($.proxy(function(ev) {
            this.scaleContent();
        }, this));
        
        $('#part-trans').append($el);

        $el.on('mouseover', $.proxy(function(ev) {
            $('#overlay').css({
                left: this.box[0]*this.ratio + 'px',
                top: this.box[1]*this.ratio + 'px',
                width: (this.box[2] - this.box[0])*this.ratio + 'px',
                height: (this.box[3] - this.box[1])*this.ratio + 'px'
            }).show();
        }, this));
        $el.on('mouseleave', function(ev) {
            $('#overlay').hide();
        });

        $el.on('click', $.proxy(function(ev) {
            this.edit();
        }, this));
    }

    getText() {
        var selectedTranscription = $('#document-transcriptions').val();
        return this.transcriptions[selectedTranscription];
    }

    scaleContent() {
        var scaleX = ((this.box[2] - this.box[0])*this.ratio) / this.textContainer.width();
        //var scaleY = this.textContainer.height() / ((this.box[3] - this.box[1])*this.ratio);
        this.textContainer.css({
            transform: 'scaleX('+scaleX+')'
        });
    }
    
    edit () {
        currentLine = this;
        // form hidden values
        $('#line-transcription-form [name=transcription]').val($('#document-transcriptions').val());
        $('#line-transcription-form [name=line]').val(this.pk);
        
        if (this.order == 0) { $("#trans-modal #prev-btn").attr('disabled', true); }
        else { $("#trans-modal #prev-btn").attr('disabled', false); }
        if (this.order == (lines.length-1)) { $("#trans-modal #next-btn").attr('disabled', true); }
        else { $("#trans-modal #next-btn").attr('disabled', false); }

        // reset width to recalculate ratio
        $('#modal-img-container').css({width: '100%'});
        $('#trans-modal #trans-input').froalaEditor('html.set', this.getText());
        $('#trans-modal').modal('show');
        var originalWidth = (this.box[2] - this.box[0]);
        var originalHeight = (this.box[3] - this.box[1]);
        var boxWidth = $('#modal-img-container').width();
        var ratio = boxWidth / originalWidth;
        var MAX_HEIGHT = 200;
        if ((originalHeight * ratio) > MAX_HEIGHT) {
            ratio = ratio * originalHeight / MAX_HEIGHT;
        }
        $('#trans-modal #modal-img-container').animate({  // , #trans-modal .fr-box
            fontSize: originalHeight * ratio * 0.7 + 'px',
            lineHeight: originalHeight * ratio + 'px',
            height: originalHeight * ratio + 'px'
        });
        $('#trans-modal #modal-img-container').css({
            width: originalWidth * ratio + 'px'});
        
        $('#trans-modal #line-img').animate({
            left: '-'+this.box[0]*ratio+'px',
            top: '-'+this.box[1]*ratio+'px',
            width: this.imgWidth*ratio + 'px'
        });
    }

    save() {
        var selectedTranscription = $('#document-transcriptions').val();
        if (this.transcriptions[selectedTranscription] != $('#trans-input', $form).val()) {
            // content changed
            this.transcriptions[selectedTranscription] = $('#trans-input', $form).val();
            this.textContainer.html($('#trans-input', $form).val());
            this.textContainer.ready($.proxy(function(ev) {
                this.scaleContent();
            }, this));
            var $form = $('#trans-modal #line-transcription-form');
            $.post($form.attr('action'), $form.serialize());
        }
    }
}

$(document).ready(function() {
    var $container = $('#img-container');
    WheelZoom($container);
    $container.get(0).addEventListener('wheelzoom.update', function(ev) {
        $('#part-trans').css({
            transform: 'translate('+ev.detail.translate.x+'px,'+ev.detail.translate.y+'px) scale('+ev.detail.scale+')'
        });
    });
    
    $("#trans-modal").draggable({
        handle: ".modal-header"
    });
    $("#trans-modal #prev-btn").click(function(ev) {
        lines[currentLine.order-1].edit();
    });
    $("#trans-modal #next-btn").click(function(ev) {
        lines[currentLine.order+1].edit();
    });

    $('#trans-input').on('froalaEditor.blur', function (e, editor) {
        currentLine.save();
    });    
});
