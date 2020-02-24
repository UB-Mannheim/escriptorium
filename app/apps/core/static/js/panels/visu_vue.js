var TranscriptionModal = Vue.component('transcriptionmodal', {
    props: ['line'],
    mounted() {
        this.computeStyles();
    },
    watch: {
        'line' : function (new_, old_) {
            this.computeStyles();
        }
    },
    computed: {
        localTranscription: {
            get() {
                return this.line.transcription.content;
            },
            set(newValue) {
                this.line.transcription.content = newValue;
                // is this ok ?
                this.$parent.$parent.$emit('update:transcription', this.line.transcription);
            }
        }
    },
    methods: {
        close() {
            this.$parent.editLine = null;
            $(this.$el).modal('hide');
        },
        computeStyles() {
            // this.zoom.reset();
            // needs to be shown BEFORE doing calculations!
            $(this.$el).modal('show');
            
            let modalImgContainer = this.$el.querySelector('#modal-img-container');
            let img = modalImgContainer.querySelector('img#line-img');
            let hContext = 0.35; // vertical context added around the line, in percentage
            
            let poly = this.line.mask || this.line.baseline;
            let minx = Math.min.apply(null, poly.map(pt => pt[0]));
            let miny = Math.min.apply(null, poly.map(pt => pt[1]));
            let maxx = Math.max.apply(null, poly.map(pt => pt[0]));
            let maxy = Math.max.apply(null, poly.map(pt => pt[1]));
            let width = maxx - minx;
            let height = maxy - miny;
            
            // we use the same same vertical context horizontaly
            let ratio = modalImgContainer.clientWidth / (width + (2*height*hContext));

            var MAX_HEIGHT = Math.round(Math.max(25, (document.body.clientHeight-200) / 3));
            let lineHeight = Math.max(10, Math.round(height*ratio));
            if (lineHeight > MAX_HEIGHT) {
                // change the ratio so that the image can not get too big
                ratio = (MAX_HEIGHT/lineHeight)*ratio;
                lineHeight = MAX_HEIGHT;
            }
            let context = hContext*lineHeight;
            let visuHeight = lineHeight + 2*context;
            
            modalImgContainer.style.height = visuHeight+'px';
            img.style.width = this.$parent.part.image.size[0]*ratio +'px';
            
            let left = Math.round(minx*ratio)-context;
            let top = Math.round(miny*ratio)-context;
            img.style.marginLeft = -left+'px';
            img.style.marginTop = -top+'px';
            
            // Content input
            let input = this.$el.querySelector('#trans-modal #trans-input');
            let content = input.value;
            let ruler = document.createElement('span');
            ruler.style.position = 'absolute';
            ruler.style.visibility = 'hidden';
            ruler.textContent = content;
            document.body.appendChild(ruler);
            
            let fontHeight = Math.min(lineHeight, 60);
            ruler.style.fontSize = fontHeight+'px';
            input.style.fontSize = fontHeight+'px';
            input.style.height = fontHeight+10+'px';
            if (READ_DIRECTION == 'rtl') {
                input.style.marginRight = context+'px';
            } else {
                input.style.marginLeft = context+'px';
            }
            if (content) {
                let lineWidth = width*ratio;
                var scaleX = Math.min(5,  lineWidth / ruler.clientWidth);
                scaleX = Math.max(0.2, scaleX);
                scaleX = Math.min(2, scaleX);
                input.style.transform = 'scaleX('+ scaleX +')';
                input.style.width = 'calc('+100/scaleX + '% - '+context/scaleX+'px)'; // fit in the container
            } else {
                input.style.transform = 'none';
                input.style.width = 'calc(100% - '+context+'px)';
            }
            document.body.removeChild(ruler);  // done its job
            
            input.focus();
            
            // Overlay
            let overlay = modalImgContainer.querySelector('.overlay');
            if (this.line.mask) {
                let maskPoints = this.line.mask.map(
                    pt => Math.round(pt[0]*ratio-left)+ ' '+
                          Math.round(pt[1]*ratio-top)).join(',');
                overlay.querySelector('polygon').setAttribute('points', maskPoints);
                overlay.style.display = 'block';
            } else {
                overlay.style.display = 'none';
            }
        },
        
        showHistory() {
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
        },        
    },
});

var visuLine = Vue.extend({
    props: ['line', 'ratio'],
    updated() {
        this.$nextTick(this.reset);
    },
    methods: {
        computeLineHeight() {
            let lineHeight;
            if (this.line.mask) {
                let poly = this.line.mask.flat(1).map(pt => Math.round(pt));
                var area = 0;
                // A = 1/2(x_1y_2-x_2y_1+x_2y_3-x_3y_2+...+x_(n-1)y_n-x_ny_(n-1)+x_ny_1-x_1y_n), 
                for (let i=0; i<poly.length; i++) {
                    let j = (i+1) % poly.length; // loop back to 1
                    area += poly[i][0]*poly[j][1] - poly[j][0]*poly[i][1];
                }
                area = Math.abs(area*this.ratio);
                lineHeight = area / this.pathElement.getTotalLength();
            } else {
                lineHeight = 30;
            }
            
            lineHeight = Math.max(Math.min(Math.round(lineHeight), 100), 5);
            this.textElement.style.fontSize =  lineHeight * (1/2) + 'px';
        },
        
        computeTextLength() {
            content = this.line.transcription && this.line.transcription.content;
            if (content) {
                this.polyElement.setAttribute('stroke', 'none');
                this.pathElement.setAttribute('stroke', 'none');
                
                // adjust the text length to fit in the box
                let textLength = this.textElement.getComputedTextLength();
                let pathLength = this.pathElement.getTotalLength();
                if (textLength && pathLength) {
                    this.textElement.setAttribute('textLength', pathLength+'px');
                }
            } else {
                // TODO: not dry
                this.polyElement.setAttribute('stroke', 'lightgrey');
                this.pathElement.setAttribute('stroke', 'blue');
            }
        },
        
        showOverlay() {
            if (this.line.mask) {
                Array.from(document.querySelectorAll('.panel-overlay')).map(
                    function(e) {
                        // TODO: transition
                        e.style.display = 'block';
                        e.querySelector('polygon').setAttribute('points', this.maskPoints);
                    }.bind(this)
                );
            }
        },
        hideOverlay() {
            Array.from(document.querySelectorAll('.panel-overlay')).map(
                function(e) {
                    e.style.display = 'none';
                }
            );
        },
        edit() {
            this.$parent.editLine = this.line;
        },
        reset() {
            this.computeLineHeight();
            this.computeTextLength();
        },
    },
    computed: {
        polyElement() { return this.$el.querySelector('polygon'); },
        pathElement() { return this.$el.querySelector('path'); },
        textElement() { return this.$el.querySelector('text'); },
        textPathId() {
            return 'textPath'+this.line.pk;
        },
        maskPoints() {
            if (this.line.mask === null) return '';
            return this.line.mask.map(pt => Math.round(pt[0]*this.ratio)+ ' '+Math.round(pt[1]*this.ratio)).join(',');
        },
        baselinePoints() {
            var ratio = this.ratio;
            function ptToStr(pt) {
                return Math.round(pt[0]*ratio)+' '+Math.round(pt[1]*ratio);
            }
            return 'M '+this.line.baseline.map(pt => ptToStr(pt)).join(' L ');
        }
    }
});

var VisuPanel = BasePanel.extend({
    data() { return  {
        editLine: null
    };},
    components: {
        'visuline': visuLine,
    },
    mounted() {
        // wait for the element to be rendered
        Vue.nextTick(function() {
            this.$parent.zoom.register(this.$el.querySelector('#visu-zoom-container'),
                                       {map: true});
        }.bind(this));
    },
    methods: {
        editNext() {
            index = this.part.lines.indexOf(this.editLine);
            if(index < this.part.lines.length - 1) {
                this.editLine = this.part.lines[index + 1];
            }
        },
        editPrevious() {
            index = this.part.lines.indexOf(this.editLine);
            if(index >= 1) {
                this.editLine = this.part.lines[index - 1];
            }
        },
        updateView() {
            this.$el.querySelector('svg').style.height = Math.round(this.part.image.size[1] * this.ratio) + 'px';
        }
    }
});
