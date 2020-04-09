const TranscriptionModal = Vue.component('transcriptionmodal', {
    props: ['line'],
    components: {
        'lineversion': LineVersion
    },
    created() {
        this.$on('update:transcription:version', function(version) {
            this.line.currentTrans.content = version.data.content;
            this.$parent.$parent.$emit('update:transcription', this.line.currentTrans);
        }.bind(this));

        // make sure that typing in the input doesnt trigger keyboard shortcuts
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
        $(this.$el).draggable({handle: '.modal-header'});
        $(this.$el).resizable();
        this.computeStyles();
    },
    watch: {
        line(new_, old_) {
            this.computeStyles();
        }
    },
    computed: {
        momentDate() {
            return moment.tz(this.line.currentTrans.version_updated_at, this.timeZone);
        },
        modalImgSrc() {
            return this.$parent.part.image.uri;
        },
        otherTranscriptions() {
            let a = Object
                .keys(this.line.transcriptions)
                .filter(pk=>this.$parent.$parent.comparedTranscriptions
                                .includes(parseInt(pk)))
                .map(pk=>{ return {
                    pk: pk,
                    name: this.$parent.$parent.part.transcriptions.find(e=>e.pk==pk).name,
                    content: this.line.transcriptions[pk].content
                }; });
            return a;
        },
        localTranscription: {
            get() {
                return this.line.currentTrans.content;
            },
            set(newValue) {
                this.line.currentTrans.content = newValue;
                // is this ok ?
                this.$parent.$parent.$emit('update:transcription',
                                           this.line.currentTrans);
            }
        }
    },
    methods: {
        close() {
            $(this.$el).modal('hide');
        },

        comparedContent(content) {
            let diff = Diff.diffChars(this.line.currentTrans.content, content);
            return diff.map(function(part){
                let color = part.added ? 'green' :
                            part.removed ? 'red' : '';
                if (part.removed) {
                    return '<small><font color="'+color+'" class="collapse show history-deletion">'+part.value+'</font></small>';
                } else if (part.added) {
                    return '<font color="'+color+'">'+part.value+'</font>';
                } else {
                    return part.value;
                }
            }.bind(this)).join('');
        },

        computeStyles() {
            // this.zoom.reset();
            let modalImgContainer = this.$el.querySelector('#modal-img-container');
            let img = modalImgContainer.querySelector('img#line-img');
            let hContext = 0.6; // vertical context added around the line, in percentage

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
            let content = this.line.currentTrans.content;  // note: input is not up to date yet
            let ruler = document.createElement('span');
            ruler.style.position = 'absolute';
            ruler.style.visibility = 'hidden';
            ruler.textContent = content;
            ruler.style.whiteSpace="nowrap"
            container.appendChild(ruler);

            let fontSize = Math.round(lineHeight*0.7);  // Note could depend on the script
            ruler.style.fontSize = fontSize+'px';
            input.style.fontSize = fontSize+'px';
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
                input.style.width = 100/scaleX + '%';
            } else {
                input.style.transform = 'none';
                input.style.width = '100%'; //'calc(100% - '+context+'px)';
            }
            container.removeChild(ruler);  // done its job

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
