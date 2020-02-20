var SourcePanel = BasePanel.extend({
    mounted: function() {
        zoom.register(this.$el.querySelector('img'), {map: true});
    }
});
