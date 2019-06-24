class SourcePanel extends Panel {
    constructor ($panel, $tools, opened) {
        super($panel, $tools, opened);
        zoom.register(this.$container);
        $('.img-container img', this.$panel).on('load', $.proxy(function(data) {
            zoom.refresh();
        }, this));
    }
    
    load(part) {
        super.load(part);
        if (this.part.image.thumbnails.large) {
            $('.img-container img', this.$panel).attr('src', this.part.image.thumbnails.large);
        } else {
            $('.img-container img', this.$panel).attr('src', this.part.image.uri);
        }
    }
}
