class BinarizationPanel extends Panel {
    constructor ($panel, $tools, opened) {
        super($panel, $tools, opened);

        zoom.register(this.$container);
        $('.img-container img', this.$panel).on('load', $.proxy(function() {
            zoom.refresh();
        }, this));
    }
    
    load(part) {
        super.load(part);
        if (this.part.bw_image) {
            if (this.part.bw_image.thumbnails.large) {
                $('.img-container img', this.$panel).attr('src', this.part.bw_image.thumbnails.large);
            } else {
                $('.img-container img', this.$panel).attr('src', this.part.bw_image.uri);
            }
        } else {
            $('.img-container img', this.$panel).attr('src', '');
        }
    }
}
