class SourcePanel extends Panel {
    constructor ($panel, $tools, opened) {
        super($panel, $tools, opened);
        this.$img = $('.img-container img', this.$panel);
        this.zoomTarget = zoom.register($('.zoom-container', this.$container).get(0), {map: true});
    }
    
    load(part) {
        super.load(part);
        if (this.part.image.thumbnails.large) {
            this.$img.attr('src', this.part.image.thumbnails.large);
        } else {
            this.$img.attr('src', this.part.image.uri);
        }
    }
}
