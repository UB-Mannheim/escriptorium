var TranscriptionModal = Vue.component('transcriptionmodal', {
    props: ['line'],
    mounted: function() {
        // this.zoom
        this.computeStyle();
    },
    watch: {
        'line.transcription' : function (new_, old_) {
            this.computeStyle();
        }.bind(this)
    },
    methods: {
        computeStyle: function() {
            // this.zoom.reset();
            // this.showOverlay();
            let modalImgContainer = this.$el.querySelector('#modal-img-container');
            let img = modalImgContainer.querySelector('img#line-img');
            let hContext = 0.35; // in percentage

            this.$el.style.display = 'block';
            
            let poly = this.line.mask || this.line.baseline;
            let minx = Math.min.apply(null, poly.map(pt => pt[0]));
            let miny = Math.min.apply(null, poly.map(pt => pt[1]));
            let maxx = Math.max.apply(null, poly.map(pt => pt[0]));
            let maxy = Math.max.apply(null, poly.map(pt => pt[1]));
            let width = maxx - minx;
            let height = maxy - miny;
            
            let panelToTransRatio = modalImgContainer.getBoundingClientRect().width /
                (width+2*height*hContext);

            var MAX_HEIGHT = Math.max(25, (document.body.clientHeight-400) / 3);
            let lineHeight = Math.max(10, Math.round(height*panelToTransRatio));
            if (lineHeight > MAX_HEIGHT) {
                // change the ratio so that the image can not get too big
                panelToTransRatio = (MAX_HEIGHT/lineHeight)*panelToTransRatio;
                lineHeight = MAX_HEIGHT;
            }
            let context = hContext*lineHeight;
            let visuHeight = lineHeight + 2*context;
            
            modalImgContainer.style.height = visuHeight+'px';
            // img.style.width = this.panel.$panel.width()*panelToTransRatio +'px';            
            
            let left = Math.round(minx*panelToTransRatio)-context;
            let top = Math.round(miny*panelToTransRatio)-context;
            img.style.left = -left+'px';
            img.style.top = -top+'px';

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
                let lineWidth = width*panelToTransRatio;
                var scaleX = Math.min(5,  lineWidth / ruler.clientWidth);
                scaleX = Math.max(0.2, scaleX);
                input.style.transform = 'scaleX('+ scaleX +')';
                input.style.width = 'calc('+100/scaleX + '% - '+context/scaleX+'px)'; // fit in the container
            } else {
                input.style.transform = 'none';
                input.style.width = 'calc(100% - '+context+'px)';
            }
            document.body.removeChild(ruler);  // done its job
            
            input.focus();

        },

        showOverlay: function() {
            // Overlay
            let modalImgContainer = this.$el.querySelector('#modal-img-container');
            let overlay = modalImgContainer.querySelector('.overlay');
            let coordToTransRatio = this.panel.part.image.size[0] / img.width;
            if (this.mask) {
                let polygon = this.mask.map(pt => {
                    return Math.round(pt[0]/coordToTransRatio-left)+ ' '+
                        Math.round(pt[1]/coordToTransRatio-top);
                }).join(',');
                overlay.querySelector('polygon').setAttribute('points', polygon);
                overlay.style.display = 'block';
            } else {
                overlay.style.display = 'none';
            }
        },
        
        showHistory: function() {
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
    props: ['line'],
    // data: function() { return {
    //     polyElement: null,
    //     pathElement: null,
    //     textElement: null
    // };},
    updated: function() {
        this.$nextTick(function () { this.reset(); });
    },
    methods: {
        getPolyElement: function() { return this.polyElement},
        getPathElement: function() { return this.pathElement},
        computeLineHeight: function() {
            let lineHeight;
            if (this.line.mask) {
                let poly = this.line.mask.flat(1).map(pt => Math.round(pt));
                var area = 0;
                // A = 1/2(x_1y_2-x_2y_1+x_2y_3-x_3y_2+...+x_(n-1)y_n-x_ny_(n-1)+x_ny_1-x_1y_n), 
                for (let i=0; i<poly.length; i++) {
                    let j = (i+1) % poly.length; // loop back to 1
                    area += poly[i][0]*poly[j][1] - poly[j][0]*poly[i][1];
                }
                let ratio = this.$parent.getRatio();
                area = Math.abs(area*ratio);
                lineHeight = area / this.pathElement.getTotalLength();
            } else {
                lineHeight = 30;
            }
            
            lineHeight = Math.max(Math.min(Math.round(lineHeight), 100), 5);
            this.textElement.style.fontSize =  lineHeight * (1/2) + 'px';
        },

        computeTextLength: function() {
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
        
        showOverlay: function() {
            if (this.line.mask) {
                Array.from(document.querySelectorAll('.overlay')).map(
                    function(e) {
                        // TODO: transition
                        e.style.display = 'block';
                        e.querySelector('polygon').setAttribute('points', this.maskPoints);
                    }.bind(this)
                );
            }
        },
        hideOverlay: function() {
            Array.from(document.querySelectorAll('.overlay')).map(
                function(e) {
                    e.style.display = 'none';
                }
            );
        },
        edit: function() {
            this.$parent.editLine = this.line;
        },
        editNext: function() {
            //todo
        },
        editPrevious: function() {
            //todo
        },
        reset: function() {
            this.computeLineHeight();
            this.computeTextLength();
        },
    },
    computed: {
        polyElement: function() { return this.$el.querySelector('polygon'); },
        pathElement: function() { return this.$el.querySelector('path'); },
        textElement : function() { return this.$el.querySelector('text'); },
        textPathId: function() {
            return 'textPath'+this.line.pk;
        },
        maskPoints: function() {
            let ratio = this.$parent.getRatio();
            return this.line.mask.map(pt => Math.round(pt[0]*ratio)+ ' '+Math.round(pt[1]*ratio)).join(',');
        },
        baselinePoints: function() {
            var ratio = this.$parent.getRatio();
            function ptToStr(pt) {    
                return Math.round(pt[0]*ratio)+' '+Math.round(pt[1]*ratio);
            }
            return 'M '+this.line.baseline.map(pt => ptToStr(pt)).join(' L ');
        }
    }
        
});

var VisuPanel = BasePanel.extend({
    data: function() { return {
        editLine: null,
    };},
    components: {
        'visuline': visuLine,
    },
    mounted: function() {
        let ratio = this.getRatio();
        this.$el.setAttribute('height', Math.round(this.part.image.size[1]*ratio));
        // zoom.register(this.$el.querySelector('svg'), {map: true});
    }
});
