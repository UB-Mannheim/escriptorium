var SourcePanel = BasePanel.extend({
    mounted: function() {
        this.$parent.zoom.register(this.$el.querySelector('img'), {map: true});
    }
});
