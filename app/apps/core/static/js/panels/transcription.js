'use strict';
var currentLine = null;
var my_zone = moment.tz.guess();
var SvgNS = "http://www.w3.org/2000/svg";

class TranscriptionLine {
    constructor (line, panel) {
        this.pk = line.pk;
        this.mask = line.mask;
        this.baseline = line.baseline;
        this.order = line.order;
        
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

    makeShape() {
        var ratio = this.panel.getRatio();
        function ptToStr(pt) {
            return Math.round(pt[0]*ratio)+' '+Math.round(pt[1]*ratio);
        }

        if (this.mask) {
            let poly = this.mask.flat(1).map(pt => Math.round(pt*ratio));
            this.polyElement.setAttribute('points', poly);

            var area = 0;
            // A = 1/2(x_1y_2-x_2y_1+x_2y_3-x_3y_2+...+x_(n-1)y_n-x_ny_(n-1)+x_ny_1-x_1y_n), 
            for (let i=0; i<this.mask.length; i++) {
                let j = (i+1)%this.mask.length; // loop back to 1
                area += this.mask[i][0]*this.mask[j][1] - this.mask[j][0]*this.mask[i][1];
            }
            area = Math.abs(area*ratio/2);
        }
        var path;
        if (this.baseline) {
            path = 'M '+this.baseline.map(pt => ptToStr(pt)).join(' L ');
        } else {
            // create a fake path based on the mask
            if (READ_DIRECTION == 'rtl') path = 'M '+ptToStr(this.mask[2])+' T '+ptToStr(this.mask[1]);
            else path = 'M '+ptToStr(this.mask[1])+' T '+ptToStr(this.mask[2]);
        }
        
        this.pathElement.setAttribute('d', path);
        let lineHeight, pathLength = this.pathElement.getTotalLength();
        if (this.mask) {
            lineHeight = area / pathLength;
        } else {
            lineHeight = 30;
        }
        lineHeight = Math.max(Math.min(Math.round(lineHeight), 100), 5);
        this.textElement.style.fontSize =  lineHeight * (1/2) + 'px';
    }
    
    reset() {
        this.makeShape();
        this.setText();
    }
    
    update(line) {
        this.pk = line.pk;
        this.mask = line.mask;
        this.baseline = line.baseline;
        this.makeShape();
    }
    
    showOverlay() {
        let ratio = this.panel.getRatio();
        let polygon = this.mask.map(pt => Math.round(pt[0]*ratio)+ ' '+Math.round(pt[1]*ratio)).join(',');
        $('.panel .overlay polygon').attr('points', polygon);
        $('.panel .overlay').stop(true).fadeIn(0.2);
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
        let content = this.getText();
        this.textElement.querySelector('textPath').textContent = content;
        if (content) {
            this.polyElement.setAttribute('stroke', 'none');
            this.pathElement.setAttribute('stroke', 'none');
        }
        
        // adjust the text length to fit in the box
        let textLength = this.textElement.getComputedTextLength();
        let pathLength = this.pathElement.getTotalLength();
        if (textLength && pathLength) {
            // this.textElement.setAttribute('textanchor', "middle");
            this.textElement.setAttribute('textLength', pathLength+'px');
        }
        
    }
    
    edit () {
        // opens the modal and setup the line editing form
        if (currentLine) currentLine.editing = false;
        this.editing = true;
        this.showOverlay();

        var content = this.getText();
        currentLine = this;

        // Pagination
        let prevBtn = document.querySelector("#trans-modal #prev-btn");
        let nextBtn = document.querySelector("#trans-modal #next-btn");
        if (this.order == 0) { prevBtn.disabled = true; }
        else { prevBtn.disabled = false; }
        if (this.order == (this.panel.lines.length-1)) { nextBtn.disabled = true; }
        else { nextBtn.disabled = false; }

        $('#trans-modal').modal('show');
        
        let modalImgContainer = document.querySelector('#modal-img-container');
        let img = modalImgContainer.querySelector('img#line-img');
        let bounds = this.polyElement.getBBox();
        // img.style.transform = 'none';  // reset img width for calculations
        let panelToImgRatio = this.panel.$panel.width() / img.width;
        let panelToTransRatio = modalImgContainer.getBoundingClientRect().width / bounds.width;

        // Line image
        let context = 20;
        modalImgContainer.style.height = Math.round(bounds.height*panelToTransRatio)+2*context+'px';
        img.style.width = this.panel.$panel.width()*panelToTransRatio + 'px';
        
        let left = Math.round(bounds.x*panelToTransRatio);
        let top = Math.round(bounds.y*panelToTransRatio);
        img.style.left = -left+'px';
        img.style.top = -top+context+'px';
        
        // Overlay
        let overlay = modalImgContainer.querySelector('.overlay');
        let coordToTransRatio = this.panel.part.image.size[0] / img.width;
        let polygon = this.mask.map(pt => {
            return Math.round(pt[0]/coordToTransRatio-left)+ ' '+
                   Math.round(pt[1]/coordToTransRatio-top+context);
        }).join(',');
        overlay.querySelector('polygon').setAttribute('points', polygon);

        // Content input
        let input = document.querySelector('#trans-modal #trans-input');
        document.querySelector('#trans-modal #trans-input').value = content;
        let ruler = document.createElement('span');
        ruler.style.position = 'absolute';
        ruler.style.visibility = 'hidden';
        ruler.textContent = content;
        document.body.appendChild(ruler);
        let lineHeight = Math.min(60, bounds.height*panelToTransRatio);
        ruler.style.fontSize = lineHeight+'px';
        input.style.fontSize = lineHeight+'px';
        input.style.height = lineHeight+10+'px';
        if (content) {
            var scaleX = Math.min(5,  modalImgContainer.clientWidth / ruler.clientWidth);
            scaleX = Math.max(0.2, scaleX);
            input.style.transform = 'scaleX('+ scaleX +')';
            input.style.width = 100/scaleX + '%'; // fit in the container
        } else {
            input.style.transform = 'none';
            input.style.width = '100%';
        }
        document.body.removeChild(ruler);  // done its job
        
        input.focus();
        
        // History
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
        this.zoomTarget = zoom.register($('.zoom-container', this.$container).get(0), {map: true});

        // load the user saved transcription
        let itrans = userProfile.get('initialTranscriptions');
        if (itrans && itrans[DOCUMENT_ID]) {
            $('#document-transcriptions').val(itrans[DOCUMENT_ID]);
        }

        // save the user default transcription on change of the select input
        this.selectedTranscription = $('#document-transcriptions').val();
        let dts = document.querySelector('#document-transcriptions');
        if (dts) dts.addEventListener('change', function(ev) {
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
        // document.querySelector('.js-export').addEventListener('click', function(ev) {
        //     ev.preventDefault();
        //     let format = ev.target.attributes['data-format'];
        //     window.open(API.document + '/export/?transcription='+this.selectedTranscription+'&as=' + format);
        // }.bind(this));

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

        function saveAndContinue() {
            currentLine.save();
            if (this.lines[currentLine.order+1]) {
                this.lines[currentLine.order+1].edit();
            } else {
                $('#trans-modal').modal('hide');
            }
        }
        document.querySelector('#trans-modal #save-continue-btn').addEventListener('click', function (e, editor) {
            saveAndContinue.bind(this)();
        }.bind(this));
        document.querySelector('#trans-modal #trans-input').addEventListener('keyup', function(e) {
	        if(e.key == 'Enter') {
	            saveAndContinue.bind(this)();
	        }
	    }.bind(this));

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
        if (this.lines) [].forEach.call(this.lines, e => this.content.removeChild(e.element));
        this.lines = [];
        
        if (this.part.image.thumbnails.large) {
            document.querySelector('#trans-modal #modal-img-container img').setAttribute('src', this.part.image.thumbnails.large);
        } else {
            document.querySelector('#trans-modal #modal-img-container img').setAttribute('src', this.part.image.uri);
        }
        for (var i=0; i < this.part.lines.length; i++) {
            this.addLine(this.part.lines[i]);
        }
        
        this.loadTranscriptions();
        // this.refresh();
    }
    
    refresh() {
        if (this.opened) {
            for (var i=0; i<this.lines.length; i++) {
                this.lines[i].reset();
            }
        }
    }
}
