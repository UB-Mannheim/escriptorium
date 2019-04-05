class BinarizationPanel {
    constructor ($panel, opened) {
        this.$panel = $panel;
        this.opened = opened | false;
        this.$container = $('.img-container', this.$panel);
        WheelZoom(this.$container, false, 1, 1);
    }

    load(part) {
        this.part = part;
        if (this.part.bw_image) {
            if (this.part.bw_image.thumbnails) {
                $('.img-container img', this.$panel).attr('src', this.part.bw_image.thumbnails.large);
            } else {
                $('.img-container img', this.$panel).attr('src', this.part.bw_image.url);
            }
        } else {
            $('.img-container img', this.$panel).attr('src', '');
        }
        if (this.opened) this.open();
        this.$container.trigger('wheelzoom.refresh');
    }
    
    open() {
        this.opened = true;
        this.$panel.show();
        Cookies.set('binar-panel-open', true);
    }
    
    close() {
        this.opened = false;
        this.$panel.hide();
        Cookies.set('binar-panel-open', false);
    }
    
    toggle() {
        if (this.opened) this.close();
        else this.open();
    }
    
    reset() {
        this.$container.trigger('wheelzoom.refresh');
    }
}
