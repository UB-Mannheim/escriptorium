class SourcePanel {
    constructor ($panel, opened) {
        this.$panel = $panel;
        this.opened = opened | false;
        this.$container = $('.img-container', this.$panel);
        zoom.register(this.$container);
    }

    load(part) {
        this.part = part;

        $('.img-container img', this.$panel).on('load', $.proxy(function() {
            zoom.refresh();
        }, this));

        if (this.part.image.thumbnails) {
            $('.img-container img', this.$panel).attr('src', this.part.image.thumbnails.large);
        } else {
            $('.img-container img', this.$panel).attr('src', this.part.image.url);
        }
        if (this.opened) this.open();
    }
    
    open() {
        this.opened = true;
        this.$panel.show();
        Cookies.set('img-panel-open', true);
    }

    close() {
        this.opened = false;
        this.$panel.hide();
        Cookies.set('img-panel-open', false);
    }

    toggle() {
        if (this.opened) this.close();
        else this.open();
    }

    reset() {
        zoom.refresh();
    }
}
