const SourcePanel = BasePanel.extend({
    mounted: function() {
        this.$parent.zoom.register(
            this.$el.querySelector('#source-zoom-container'), 
            {map: true});
    }
});
