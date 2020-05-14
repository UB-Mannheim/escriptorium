/*
Visual transcription panel (or visualisation panel)
*/

const VisuPanel = BasePanel.extend({
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
