'use strict';
var currentLine = null;
var my_zone = moment.tz.guess();
var SvgNS = "http://www.w3.org/2000/svg";

class TranscriptionLine {
    constructor (line, panel) {
        //Object.assign(this, line);
        this.pk = line.pk;
        this.mask = line.mask;
        this.baseline = line.baseline;
        
        this.editing = false;
        this.panel = panel;
        this.transcriptions = {};
        this.page = document.getElementById('part-trans');
        
        this.api = this.panel.api + 'transcriptions/';

        // copy template
        let tmp = document.getElementById('line-template');
        let newNode = tmp.cloneNode(true);
        newNode.setAttribute('id', 'trans-box-line-'+this.pk);
        let [polyElement, pathElement, textElement] = newNode.children;
        textElement.children[0].setAttribute('href', '#textPath'+this.pk);
                
        this.element = newNode;
        this.panel.content.appendChild(newNode);
        this.element.classList.add('trans-box');

        this.polyElement = polyElement;
        this.textElement = textElement;
        this.pathElement = pathElement;
        this.pathElement.setAttribute('id', 'textPath'+this.pk);
        
        this.update(line);
        this.setText();

        this.element.setAttribute('pointer-events', 'visible');  // allows to click inside fill='none' elements
        this.element.addEventListener('mouseover', function(ev) {
            this.showOverlay();
        }.bind(this));
        this.element.addEventListener('mouseleave', function(ev) {
            if (!this.editing) $('.panel .overlay').fadeOut({queue:false});
        }.bind(this));
        this.element.addEventListener('click', function(ev) {
            this.edit();
        }.bind(this));
    }
    
    reset() {
        this.setText();
    }

    update(line) {
        this.pk = line.pk;
        this.mask = line.mask;
        this.baseline = line.baseline;

        var ratio = this.panel.ratio;
        function ptToStr(pt) {
            return Math.round(pt[0]*ratio)+' '+Math.round(pt[1]*ratio);
        }
        
        let poly = this.mask.flat(1).map(pt => Math.round(pt*this.panel.ratio));
        this.polyElement.setAttribute('points', poly);
        
        var path;
        if (this.baseline) {
            path = 'M '+this.baseline.map(pt => ptToStr(pt)).join(' L ');
        } else {
            // create a fake path based on the mask
            if (READ_DIRECTION == 'rtl') path = 'M '+ptToStr(this.mask[2])+' T '+ptToStr(this.mask[1]);
            else path = 'M '+ptToStr(this.mask[1])+' T '+ptToStr(this.mask[2]);
            // console.log(newNode);
        }
        
        this.pathElement.setAttribute('d', path);
    }
    
    showOverlay() {
        // $('.panel .overlay').css({
        //     left: this.box[0]*this.panel.ratio + 'px',
        //     top: this.box[1]*this.panel.ratio + 'px',
        //     width: (this.box[2] - this.box[0])*this.panel.ratio + 'px',
        //     height: (this.box[3] - this.box[1])*this.panel.ratio + 'px'
        // }).stop(true).fadeIn(0.2);
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
        this.textElement.querySelector('textPath').textContent = this.getText();
        // adjust the text length to fit in the box
        let textLength = this.textElement.getComputedTextLength();
        let pathLength = this.pathElement.getTotalLength();
        if (textLength && pathLength) {
            this.textElement.setAttribute('textLength', pathLength);
        }
    }
    
    edit () {
        if (currentLine) currentLine.editing = false;
        this.editing = true;
        this.showOverlay();

        var content = this.getText();
        currentLine = this;
        let prevBtn = document.querySelector("#trans-modal #prev-btn");
        let nextBtn = document.querySelector("#trans-modal #next-btn");
        if (this.order == 0) { prevBtn.disabled = true; }
        else { prevBtn.disabled = false; }
        if (this.order == (this.panel.lines.length-1)) { nextBtn.disabled = true; }
        else { nextBtn.disabled = false; }

        document.querySelector('#trans-modal #trans-input').value = content;
        document.querySelector('#trans-modal #trans-rule').textContent = content;
        
        // fill the history
        let container = document.querySelector('#trans-modal #history tbody');
        while (container.firstChild) {
            container.removeChild(container.firstChild);
        }
        var lt = this.getLineTranscription();
        var noVersionBtn = document.querySelector('#no-versions');
        if (lt !== undefined) {
            document.querySelector('#new-version-btn').disabled = false;
            var versions = lt.versions;
            if (versions && versions.length > 0) {
                noVersionBtn.style.display = 'none';
                for (var i=versions.length-1; i>=0; i--) {
                    this.addVersionLine(versions[i]);
                }
            } else {
                noVersionBtn.style.display = 'block';
            }
        } else {
            noVersionBtn.style.display = 'block';
            document.querySelector('#new-version-btn').disabled = true;
        }

        // reset width to recalculate ratio
        let modalImgContainer = document.querySelector('#modal-img-container');
        modalImgContainer.style.width = '80%';
        
        // need to show the modal before calculating sizes
        $('#trans-modal').modal('show');
        var boxWidth = modalImgContainer.width();
        var ratio = boxWidth / modalImgContainer.originalWidth;
        let originalHeight = modalImgContainer.originalHeight;
        var MAX_HEIGHT = 200;
        if ((originalHeight * ratio) > MAX_HEIGHT) {
            ratio = ratio * originalHeight / MAX_HEIGHT;
        }
        let line_height = originalHeight * ratio;
        // multiply by 1.4 to add a bit of context
        let height = Math.max(Math.min(line_height*1.4, 200), 40);
        let width = modalImgContainer.originalWidth * ratio;
        let context_top = (height - line_height) / 2;
        document.querySelector('#trans-modal #modal-img-container').style.update({
            height: height + 'px',  // adds some context
            width: width + 'px'
        });
        document.querySelector('#trans-modal .overlay').style.update({
            height: line_height + 'px',
            width: width + 'px',
            top: context_top
        });
        
        // try to make the input match the image
        let el = document.querySelector('#trans-modal #trans-input');
        // $el.css({
        //     display: 'inline-block',  // change to inline-block temporarily to calculate width
        //     width: 'auto',
        //     fontSize: height * 0.7 + 'px',
        //     lineHeight: height + 'px',
        //     height: height + 'px'
        // });
        // if (content) {
        //     var scaleX = Math.min(5, originalWidth * ratio / $('#trans-rule').width());
        //     scaleX = Math.max(0.2, scaleX);
        //     $el.css({
        //         transform: 'scaleX('+ scaleX +')',
        //         width: 100/scaleX + '%' // fit in the container
        //     });
        // } else {
        //     $el.css({transform: 'none', width: '100%'});
        // }
        // $el.css({display: 'block'}); // revert to block to take the full space available
        
        // $('#trans-modal #line-img').animate({
        //     left: '-'+this.box[0]*ratio+'px',
        //     top: '-'+(this.box[1]*ratio-context_top)+'px',
        //     width: this.panel.part.image.size[0]*ratio + 'px'
        // }, 200);

        el.focus();
    }

    addVersionLine(version) {
        // var $container = document.querySelector('#trans-modal > #history tbody');
        // var date = version.updated_at.replace('T', ' ');  // makes it moment.js compliant
        // date = date.substring(0, 23) + date.substring(26);
        // var $version = $('<tr id="rev-'+version.revision+'">'+
        //                  '<th class="js-version-content w-75">'+version.data.content+'</th>'+
        //                  '<td>'+version.author+(version.source?'<br/>'+version.source:'')+'</td>'+
        //                  '<td class="js-version-date" data-date="'+date+'"></td>'+
        //                  '<td><button class="btn btn-sm btn-info js-pull-state" title="Load this state" data-rev="rev-'+version.revision+'">'+
        //                       '<i class="fas fa-file-upload"></i></button></td>'+
        //                  '</tr>');
        // var $date = $('.js-version-date', $version);
        // var mom = moment.tz($date.data('date'), my_zone);
        // $date.html(mom.fromNow());
        // $date.attr('title', "Last changed: "+mom.format('LLLL'));
        // $container.prepend($version);
    }
    
    pushVersion() {
        // var lt = this.getLineTranscription();
        // var uri = this.api + lt.pk + '/new_version/';
        // $.post(uri, {}).done($.proxy(function(data) {
        //     $('#no-versions').hide();
        //     // this.getLineTranscription().versions.splice(0, 0, data);
        //     this.addVersionLine(data);
        // }, this)).fail(function(data) {
        //     alert(data);
        // });
    }
    
    save() {
        var new_content = document.querySelector('#trans-modal #trans-input').value;
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
        this.element.parentNode.removeChild(this.element);
    }
}

class TranscriptionPanel extends Panel {
    constructor ($panel, $tools, opened) {
        super($panel, $tools, opened);
        this.part = null;
        this.lines = {};  // list of TranscriptionLine != this.part.lines

        let container = document.getElementById('part-trans');
        this.content = container.getElementsByTagName('svg')[0];

        this.zoomTarget = zoom.register(this.content, {map: true});

        // load the user saved transcription
        let itrans = userProfile.get('initialTranscriptions');
        if (itrans && itrans[DOCUMENT_ID]) {
            $('#document-transcriptions').val(itrans[DOCUMENT_ID]);
        }

        // save the user default transcription on change of the select input
        this.selectedTranscription = $('#document-transcriptions').val();
        document.querySelector('#document-transcriptions').addEventListener('change', function(ev) {
            this.selectedTranscription = document.querySelector('#document-transcriptions').value;
            // for (var i=0; i<this.lines.length; i++) {
            //     this.lines[i].reset();
            // }
            let data = {};
            data[DOCUMENT_ID] = this.selectedTranscription;
            this.loadTranscriptions();
            userProfile.set('initialTranscriptions', data);
        }.bind(this));
        
        /* export */
        document.querySelector('.js-export').addEventListener('click', function(ev) {
            ev.preventDefault();
            let format = ev.target.attributes['data-format'];
            window.open(API.document + '/export/?transcription='+this.selectedTranscription+'&as=' + format);
        }.bind(this));

        // TODO!
        // $("#trans-modal").draggable({
        //     handle: ".modal-header"
        // });
        document.querySelector("#trans-modal").addEventListener('hide.bs.modal', function(ev) {
            currentLine.editing = false;
            $('.panel .overlay').fadeOut({queue:false});
        });
        document.querySelector("#trans-modal #prev-btn").addEventListener('click', function(ev) {
            this.lines[currentLine.order-1].edit();
        }.bind(this));
        document.querySelector("#trans-modal #next-btn").addEventListener('click', function(ev) {
            this.lines[currentLine.order+1].edit();
        }.bind(this));
        document.querySelector('#trans-modal #new-version-btn').addEventListener('click', function (e, editor) {
            currentLine.pushVersion();
            $('#history').addClass('show');
        }.bind());
        document.querySelector('#trans-modal #save-btn').addEventListener('click', function (e, editor) {
            currentLine.save();
            $('#trans-modal').modal('hide');
        }.bind());
        document.querySelector('#trans-modal #save-continue-btn').addEventListener('click', function (e, editor) {
            currentLine.save();
            if (this.lines[currentLine.order+1]) {
                this.lines[currentLine.order+1].edit();
            } else {
                document.querySelector('#trans-modal').modal('hide');
            }
        }.bind(this));
        // TODO
        // document.querySelector(document).keydown(function(e) {
	    //     if(e.originalEvent.key == 'Enter') {
	    //         document.querySelector('#trans-modal #save-continue-btn').trigger('click');
	    //     }
	    // });

        // document.querySelector('#trans-modal .js-pull-state').addEventListener('click', function(ev) {
        //     ev.preventDefault();
        //     let tr = document.querySelector('tr#'+ev.target.attributes['data-rev']);
        //     document.querySelector('#trans-modal #trans-input').value = tr.querySelector('.js-version-content', $tr).textContent;
        // }.bind(this));
                
        if (this.opened) this.open();
    }

    addLine(line) {
        let newLine = new TranscriptionLine(line, this);
        this.lines.push(newLine);
    }

    getRatio() {
        return this.$panel.width() / this.part.image.size[0];
    }

    loadTranscriptions() {
        let getNext = function(page) {
            let uri = this.api + 'transcriptions/?transcription='+this.selectedTranscription+'&page=' + page;
            $.get(uri, function(data) {
                for (var i=0; i<data.results.length; i++) {
                    let cur = data.results[i];
                    let lt = this.lines.find(l => l.pk == cur.line);
                    if (lt) {
                        lt.transcriptions[this.selectedTranscription] = cur;
                        lt.reset();
                    }
                }
                if (data.next) getNext(page+1);
            }.bind(this));
        }.bind(this);
        getNext(1);
    }
    
    load(part) {
        super.load(part);
        this.lines = [];
        let lines = document.getElementsByTagName('trans-line');
        if (lines) [].forEach.call(lines, e => this.content.removeChild(e));
        this.ratio = this.getRatio();

        let container = this.content.parentNode;
        container.style.height = '100%';
        container.style.width = '100%';
        // container.style.transformOrigin = '0 0';
        // container.style.transform = 'scale('+this.ratio+')';
        
        if (this.part.image.thumbnails.large) {
            document.querySelector('#trans-modal #modal-img-container img').setAttribute('src', this.part.image.thumbnails.large);
        } else {
            document.querySelector('#trans-modal #modal-img-container img').setAttribute('src', this.part.image.uri);
        }
        for (var i=0; i < this.part.lines.length; i++) {
            this.addLine(this.part.lines[i]);
        }
        this.loadTranscriptions();
    }
    
    reset() {
        super.reset();
        if (this.opened) {
            // this.ratio = this.getRatio();
            // for (var i=0; i<this.lines.length; i++) {
            //     this.lines[i].reset();
            // }          
            // $('.zoom-container', this.$container).css({
            //     width: this.part.image.size[0]*this.ratio,
            //     height: this.part.image.size[1]*this.ratio});
        }
    }
}
