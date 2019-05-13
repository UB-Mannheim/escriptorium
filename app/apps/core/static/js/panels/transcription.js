'use strict';
var currentLine = null;
var my_zone = moment.tz.guess();

class TranscriptionLine {
    constructor (line, panel) {
        Object.assign(this, line);
        this.editing = false;
        this.panel = panel;
        this.transcriptions = {};
        
        this.api = this.panel.api + 'transcriptions/';
        var $el = $('<div id="trans-box-line-'+this.pk+'" class="trans-box"><span></span></div>');
        $el.data('TranscriptionLine', this);  // allow segmentation to target that box easily
        this.$element = $el;
        
        this.textContainer = $('span', $el).first();
        $('#part-trans').append($el);
        this.reset();
        
        $el.on('mouseover', $.proxy(function(ev) {
            this.showOverlay();
        }, this));
        $el.on('mouseleave', $.proxy(function(ev) {
            if (!this.editing) $('.overlay').fadeOut({queue:false});
        }, this));
        $el.on('click', $.proxy(function(ev) {
            this.edit();
        }, this));
    }
    
    reset() {
        this.setText();
        this.textContainer.ready($.proxy(function(ev) {
            this.setPosition();
            this.scaleContent();
        }, this));
    }
    
    setPosition() {
        this.$element.css({
            left: this.box[0]*this.panel.ratio + 'px',
            top: this.box[1]*this.panel.ratio + 'px',
            width: (this.box[2] - this.box[0])*this.panel.ratio  + 'px',
            height: (this.box[3] - this.box[1])*this.panel.ratio + 'px',
            fontSize:  (this.box[3] - this.box[1])*this.panel.ratio*0.7 + 'px',
            lineHeight: (this.box[3] - this.box[1])*this.panel.ratio + 'px'
        });
    }
    
    scaleContent() {
        this.textContainer.css({
            display: 'inline-block', // can't calculate size otherwise
            transform: 'none',
            width: 'auto'
        });
        var scaleX = (this.box[2] - this.box[0]) * this.panel.ratio / this.textContainer.width();
        let content = this.getText();
        if (content) {
            this.textContainer.css({
                transform: 'scaleX('+scaleX+')',
                width: 100/scaleX + '%', // fit in the container
            });
        } else {
            this.textContainer.css({
                transform: 'none',
                width: '100%'
            });
        }
        this.textContainer.css({display: 'block'});
    }
    
    showOverlay() {
        $('.overlay').css({
            left: this.box[0]*this.panel.ratio + 'px',
            top: this.box[1]*this.panel.ratio + 'px',
            width: (this.box[2] - this.box[0])*this.panel.ratio + 'px',
            height: (this.box[3] - this.box[1])*this.panel.ratio + 'px'
        }).stop(true).fadeIn(0.2);
    }
    
    getLineTranscription() {
        return this.transcriptions[this.panel.selectedTranscription];
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
    }
    
    edit () {
        if (currentLine) currentLine.editing = false;
        this.editing = true;
        this.showOverlay();

        var content = this.getText();
        currentLine = this;
        // form hidden values
        $('#line-transcription-form [name=transcription]').val(this.panel.selectedTranscription);
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
        let height = Math.min(originalHeight * ratio, 200);
        height = Math.max(height, 40);
        let width = originalWidth * ratio;
        
        $('#trans-modal #modal-img-container').animate({
            height: height + 'px',
            width: width + 'px'
        });
        
        // try to make the input match the image
        let $el = $('#trans-modal #trans-input, #trans-rule');
        $el.css({
            display: 'inline-block',  // change to inline-block temporarily to calculate width
            width: 'auto',
            fontSize: height * 0.7 + 'px',
            lineHeight: height + 'px',
            height: height + 'px'
        });
        if (content) {
            var scaleX = Math.min(5, originalWidth * ratio / $('#trans-rule').width());
            scaleX = Math.max(0.2, scaleX);
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
            width: this.panel.part.image.size[0]*ratio + 'px'
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
        var new_content = $('#trans-modal #trans-input').val();
        if (this.getText() != new_content) {
            var type, uri;
            var lt = this.getLineTranscription();
            if (lt === undefined) {  // creation
                type = 'POST';
                uri = this.api;
            } else { // update
                type = 'PUT';
                uri = this.api + lt.pk + '/';
            }
            
            $.ajax({type: type, url:uri, data:{
                line: this.pk,
                transcription: this.panel.selectedTranscription,
                content: new_content
            }}).done($.proxy(function(data){
                if (!lt) {  // creation
                    lt = {};
                    Object.assign(lt, data);
                    this.transcriptions[data.transcription] = lt;
                } else {
                    Object.assign(lt, data);
                }
                this.reset();
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
        this.selectedTranscription = $('#document-transcriptions').val();
        $('#document-transcriptions').change($.proxy(function(ev) {
            this.selectedTranscription = $('#document-transcriptions').val();
            for (var i=0; i<this.lines.length; i++) {
                this.lines[i].reset();
            }
            let data = {};
            data[DOCUMENT_ID] = this.selectedTranscription;
            this.loadTranscriptions();
            userProfile.set('initialTranscriptions', data);
        }, this));
        
        /* export */
        $('.js-export').click($.proxy(function(ev) {
            ev.preventDefault();
            window.open(API.document + '/export/?transcription='+this.selectedTranscription+'&as=' + $(ev.target).data('format'));
        }, this));
        
        $("#trans-modal").draggable({
            handle: ".modal-header"
        });
        $("#trans-modal").on('hide.bs.modal', function(ev) {
            currentLine.editing = false;
            $('.overlay').fadeOut({queue:false});
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
        $(document).keydown(function(e) {
	        if(e.originalEvent.key == 'Enter') {
	            $('#trans-modal #save-continue-btn').trigger('click');
	        }
	    });
        
        $('#trans-modal').on('click', '.js-pull-state', function(ev) {
            ev.preventDefault();
            var $tr = 'tr#'+$(ev.target).data('rev');
            $('#trans-modal #trans-input').val($('.js-version-content', $tr).html());
        });
                
        if (this.opened) this.open();
    }

    addLine(line, ratio) {
        this.lines.push(new TranscriptionLine(line, this));
    }

    getRatio() {
        return $('.img-container', this.$panel).width() / this.part.image.size[0];
    }

    loadTranscriptions() {
        let getNext = $.proxy(function(page) {
            let uri = this.api + 'transcriptions/?transcription='+this.selectedTranscription+'&page=' + page;
            $.get(uri, $.proxy(function(data) {
                for (var i=0; i<data.results.length; i++) {
                    let cur = data.results[i];
                    let lt = $('#trans-box-line-'+cur.line).data('TranscriptionLine');
                    lt.transcriptions[this.selectedTranscription] = cur;
                    lt.reset();
                }
                if (data.next) getNext(page+1);
            }, this));
        }, this);
        getNext(1);
    }
    
    load(part) {
        this.part = part;
        this.api = API.part.replace('{part_pk}', this.part.pk);
        this.lines = [];
        $('.trans-box').remove();
        this.ratio = this.getRatio();
        $('#trans-modal #modal-img-container img').attr('src', this.part.image.thumbnails.large);
        for (var i=0; i < this.part.lines.length; i++) {
            this.addLine(this.part.lines[i]);
        }
        this.loadTranscriptions();
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
            this.ratio = this.getRatio();
            for (var i=0; i<this.lines.length; i++) {
                this.lines[i].reset();
            }
        }
    }
}
