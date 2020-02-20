var visuLine = Vue.extend({
    props: ['line'],
    computed: {
        getMaskPolygon: function() {
            console.log('-----', this.$parent);
            let ratio = this.$parent.getRatio();
            ratio = 1;
            console.log(ratio);
            return this.line.mask.map(pt => Math.round(pt[0]*ratio)+ ' '+Math.round(pt[1]*ratio)).join(',');
        },
        getBaseline: function() {
            console.log('-----', this.$parent);
            var ratio = this.$parent.getRatio();
            ratio = 1;
            console.log(ratio);
            function ptToStr(pt) {    
                return Math.round(pt[0]*ratio)+' '+Math.round(pt[1]*ratio);
            }
            return 'M '+this.line.baseline.map(pt => ptToStr(pt)).join(' L ');
        }
    }
});

var visuPanel = BasePanel.extend({
    components: {
        'visuline': visuLine
    },
    mounted: function() {
        // zoom.register(this.$el.querySelector('img'), {map: true});
    }
});

export visuPanel;
