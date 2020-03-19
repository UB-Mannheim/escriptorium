const TranscriptionModal = Vue.component('transcriptionmodal', {
    props: ['line'],
    components: {
        'lineversion': LineVersion
    },
    created() {
        this.$on('update:transcription:version', function(version) {
            this.line.transcription.content = version.data.content;
            this.$parent.$parent.$emit('update:transcription', this.line.transcription);
        }.bind(this));

        $(document).on('hide.bs.modal', '#trans-modal', function(ev) {
            this.$parent.editLine = null;
            this.$parent.$parent.blockShortcuts = false;
        }.bind(this));

        $(document).on('show.bs.modal', '#trans-modal', function(ev) {
            this.$parent.$parent.blockShortcuts = true;
        }.bind(this));
        
        this.timeZone = moment.tz.guess();
    },
    mounted() {
        $(this.$el).modal('show');
        this.computeStyles();
    },
    watch: {
        line(new_, old_) {
            this.computeStyles();
        }
    },
    computed: {
        momentDate() {
            return moment.tz(this.line.transcription.version_updated_at, this.timeZone);
        },
        modalImgSrc() { return this.$parent.part.image.uri; },
        
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
            $(this.$el).modal('hide');
        },
        saveState() {
            this.$parent.$parent.$emit('update:transcription:new-version', this.line);
        },
        computeStyles() {
            // this.zoom.reset();
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
            var MAX_HEIGHT = Math.round(Math.max(25, (window.innerHeight-200) / 3));
            let lineHeight = Math.max(30, Math.round(height*ratio));
            if (lineHeight > MAX_HEIGHT) {
                // change the ratio so that the image can not get too big
                ratio = (MAX_HEIGHT/lineHeight)*ratio;
                lineHeight = MAX_HEIGHT;
            }
            let context = hContext*lineHeight;
            let visuHeight = lineHeight + 2*context;
            
            modalImgContainer.style.height = visuHeight+'px';
            img.style.width = this.$parent.part.image.size[0]*ratio +'px';
            
            let top = Math.round(miny*ratio)-context;
            let left = Math.round(minx*ratio)-context;
            let right = Math.round(maxx*ratio)-context;
            img.style.top = -top+'px';
            img.style.left = -left+'px';

            // Content input
            let container = this.$el.querySelector('#trans-modal #trans-input-container');
            let input = container.querySelector('#trans-input');
            let content = this.line.transcription.content;
            let ruler = document.createElement('span');
            ruler.style.position = 'absolute';
            ruler.style.visibility = 'hidden';
            ruler.textContent = content;
            document.body.appendChild(ruler);

            let fontHeight = lineHeight;
            ruler.style.fontSize = fontHeight+'px';
            input.style.fontSize = fontHeight+'px';
            input.style.lineHeight = 1.2;
            input.style.height = 'auto';
            
            if (READ_DIRECTION == 'rtl') {
                container.style.marginRight = context+'px';
            } else {
                container.style.marginLeft = context+'px';
            }
            if (content) {
                let lineWidth = width*ratio;
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
            
            // Overlay
            let overlay = modalImgContainer.querySelector('.overlay');
            if (this.line.mask) {
                let maskPoints = this.line.mask.map(
                    pt => Math.round(pt[0]*ratio-left)+ ','+
                          Math.round(pt[1]*ratio-top)).join(' ');
                overlay.querySelector('polygon').setAttribute('points', maskPoints);
                overlay.style.display = 'block';
            } else {
                overlay.style.display = 'none';
            }
        },
    },
});
