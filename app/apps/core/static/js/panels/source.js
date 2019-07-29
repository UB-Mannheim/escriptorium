class SourcePanel extends Panel {
    constructor ($panel, $tools, opened) {
        super($panel, $tools, opened);
        this.$img = $('.img-container img', this.$panel);
        zoom.register(this.$img.get(0), {map: true});
        // this.$img.on('load', $.proxy(function(data) {
        //     zoom.refresh();
        // }, this));
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
