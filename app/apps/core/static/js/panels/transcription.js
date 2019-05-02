'use strict';
var currentLine = null;
var my_zone = moment.tz.guess();

class TranscriptionLine {
    constructor (line, imgWidth, panel) {
        Object.assign(this, line);
        this.imgWidth = imgWidth;
        this.editing = false;
        this.panel = panel;
        
        this.api = API.part.replace('{part_pk}', panel.part.pk) + 'transcriptions/';
        var $el = $('<div id="trans-box-line-'+this.pk+'" class="trans-box"><span></span></div>');
        $el.data('TranscriptionLine', this);  // allow segmentation to target that box easily
        this.$element = $el;
        
        this.textContainer = $('span', $el).first();
        this.setText();        
        $('#part-trans').append($el);
        
        $el.on('mouseover', $.proxy(function(ev) {
            this.showOverlay();
        }, this));
        $el.on('mouseleave', $.proxy(function(ev) {
            if (!this.editing) $('.overlay').fadeOut();
        }, this));
        $el.on('click', $.proxy(function(ev) {
            this.edit();
        }, this));
        
        this.getRatio();
        this.setPosition();
    }

    getRatio() {
        this.ratio = $('.img-container', this.panel.$panel).width() / this.imgWidth;
    }
    
    setPosition() {
        this.$element.css({
            left: this.box[0]*this.ratio + 'px',
            top: this.box[1]*this.ratio + 'px',
            width: (this.box[2] - this.box[0])*this.ratio  + 'px',
            height: (this.box[3] - this.box[1])*this.ratio + 'px',
            fontSize:  (this.box[3] - this.box[1])*this.ratio*0.7 + 'px',
            lineHeight: (this.box[3] - this.box[1])*this.ratio + 'px'
        });
        this.scaleContent();
    }
    
    showOverlay() {
        $('.overlay').css({
            left: this.box[0]*this.ratio + 'px',
            top: this.box[1]*this.ratio + 'px',
            width: (this.box[2] - this.box[0])*this.ratio + 'px',
            height: (this.box[3] - this.box[1])*this.ratio + 'px'
        }).stop().show();
    }

    getLineTranscription() {
        let selectedTranscription = $('#document-transcriptions').val();
        return this.transcriptions && this.transcriptions.find(function(tr) {
            return tr.transcription == selectedTranscription;
        });
    }
    
    getText() {
        let lt = this.getLineTranscription();
        if (lt !== undefined) {
            return lt.content;
        } else {
            return '';
        }
    }
    setText() {
        this.textContainer.html(this.getText());
        this.scaleContent();
    }
    
    scaleContent() {
        this.textContainer.css('display', 'inline-block');
        var scaleX = Math.min(5, ((this.box[2] - this.box[0])*this.ratio) / this.textContainer.width());
        this.textContainer.css({
            transform: 'scaleX('+scaleX+')'
        });
        this.textContainer.css('display', 'block');
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
        if (this.order == (this.panel.lines.length-1)) { $("#trans-modal #next-btn").attr('disabled', true); }
        else { $("#trans-modal #next-btn").attr('disabled', false); }

        $('#trans-modal #trans-input').val(content);
        $('#trans-modal #trans-rule').html(content);
        
        // fill the history
        var $container = $('#trans-modal #history tbody');
        $container.empty();
        var lt = this.getLineTranscription();
        if (lt !== undefined) {
            $('#new-version-btn').prop('disabled', false);
            var versions = lt.versions;
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
        let $el = $('#trans-modal #trans-input, #trans-rule');
        $el.css({
            display: 'inline-block',  // change to inline-block temporarily to calculate width
            width: 'auto',
            fontSize: originalHeight * ratio * 0.7 + 'px',
            lineHeight: originalHeight * ratio + 'px',
            height: originalHeight * ratio + 'px'
        });
        if (content) {
            var scaleX = Math.min(5, originalWidth * ratio / $('#trans-rule').width());
            scaleX = Math.max(0.5, scaleX);
            $el.css({
                transform: 'scaleX('+ scaleX +')',
                width: 100/scaleX + '%' // fit in the container
            });
        } else {
            $el.css({transform: 'none', width: '100%'});
        }
        $el.css({display: 'block'}); // revert to block to take the full space available
        
        $('#trans-modal #line-img').animate({
            left: '-'+this.box[0]*ratio+'px',
            top: '-'+this.box[1]*ratio+'px',
            width: this.imgWidth*ratio + 'px'
        }, 200);

        $el.focus();
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
        var lt = this.getLineTranscription();
        var uri = this.api + lt.pk + '/new_version/';
        $.post(uri, {}).done($.proxy(function(data) {
            $('#no-versions').hide();
            // this.getLineTranscription().versions.splice(0, 0, data);
            this.addVersionLine(data);
        }, this)).fail(function(data) {
            alert(data);
        });
    }
    
    save() {
        var selectedTranscription = $('#document-transcriptions').val();
        var new_content = $('#trans-modal #trans-input').val();
        if (this.getText() != new_content) {
            var type, uri;
            var lt = this.getLineTranscription();
            if (lt === undefined) {  // creation
                type = 'POST';
                uri = this.api;
            } else { // update
                type = 'PUT';
                uri = this.api + lt.pk+'/';
            }
            $.ajax({type: type, url:uri, data:{
                line: this.pk,
                transcription: selectedTranscription,
                content: new_content
            }}).done($.proxy(function(data){
                if (!lt) {  // creation
                    lt = {};
                    Object.assign(lt, data);
                    this.transcriptions.push(lt);
                } else {
                    Object.assign(lt, data);
                }
                this.setText();
                this.textContainer.ready($.proxy(function(ev) {
                    this.scaleContent();
                }, this));
            }, this)).fail(function(data) {
                alert(data);
            });
        }
    }

    delete() {
        this.$element.remove();
    }
}

class TranscriptionPanel{
    constructor ($panel, opened) {
        this.$panel = $panel;
        this.opened = opened;
        this.part = null;
        this.lines = [];  // list of TranscriptionLine != this.part.lines
        this.$container = $('.img-container', this.$panel);

        let itrans = userProfile.get('initialTranscriptions');
        if (itrans && itrans[DOCUMENT_ID]) {
            $('#document-transcriptions').val(itrans[DOCUMENT_ID]);
        }
        $('#document-transcriptions').change($.proxy(function(ev) {
            for (var i=0; i<this.lines.length; i++) {
                this.lines[i].setText();
            }
            let data = {};
            data[DOCUMENT_ID] = $('#document-transcriptions').val();
            userProfile.set('initialTranscriptions', data);
        }, this));
        
        $("#trans-modal").draggable({
            handle: ".modal-header"
        });
        $("#trans-modal").on('hide.bs.modal', function(ev) {
            currentLine.editing = false;
            $('.overlay').fadeOut();
        });
        $("#trans-modal #prev-btn").click($.proxy(function(ev) {
            this.lines[currentLine.order-1].edit();
        }, this));
        $("#trans-modal #next-btn").click($.proxy(function(ev) {
            this.lines[currentLine.order+1].edit();
        }, this));
        $('#trans-modal #new-version-btn').on('click', function (e, editor) {
            currentLine.pushVersion();
            $('#history').addClass('show');
        });
        $('#trans-modal #save-btn').on('click', function (e, editor) {
            currentLine.save();
            $('#trans-modal').modal('hide');
        });
        $('#trans-modal #save-continue-btn').on('click', $.proxy(function (e, editor) {
            currentLine.save();
            if (this.lines[currentLine.order+1]) {
                this.lines[currentLine.order+1].edit();
            } else {
                $('#trans-modal').modal('hide');
            }
        }, this));
        $('#trans-modal').on('click', '.js-pull-state', function(ev) {
            ev.preventDefault();
            var $tr = 'tr#'+$(ev.target).data('rev');
            $('#trans-modal #trans-input').val($('.js-version-content', $tr).html());
            
        });
                
        if (this.opened) this.open();
    }

    addLine(line) {
        this.lines.push(new TranscriptionLine(line, this.part.image.size[0], this));
    }
    
    load(part) {
        this.lines = [];
        $('.trans-box').remove();
        this.part = part;
        $('#trans-modal #modal-img-container img').attr('src', this.part.image.thumbnails.large);
        for (var i=0; i < this.part.lines.length; i++) {
            this.addLine(this.part.lines[i]);
        }
        zoom.register(this.$container, true);
    }
    
    open() {
        this.opened = true;
        this.$panel.show();
        Cookies.set('trans-panel-open', true);
    }
       
    close() {
        this.opened = false;
        this.$panel.hide();
        Cookies.set('trans-panel-open', false);
    }
    
    toggle() {
        if (this.opened) this.close();
        else this.open();
    }
    
    reset() {
        if (this.opened) {
            for (var i=0; i<this.lines.length; i++) {
                this.lines[i].getRatio();
                this.lines[i].setPosition();
            }
        }
    }
}
