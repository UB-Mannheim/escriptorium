class SourcePanel {
    constructor ($panel, opened) {
        this.$panel = $panel;
        this.opened = opened | false;
        this.$container = $('.img-container', this.$panel);
        WheelZoom(this.$container, false, 1, 1);
    }

    load(part) {
        this.part = part;
        $('.img-container img', this.$panel).attr('src', this.part.image.thumbnails.large);
        if (this.opened) this.open();
        this.$container.trigger('wheelzoom.refresh');
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
        this.$container.trigger('wheelzoom.refresh');
    }
}
