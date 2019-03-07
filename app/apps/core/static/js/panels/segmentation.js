class SegmentationPanel {
    constructor ($panel, opened) {
        this.$panel = $panel;
        this.opened = opened | false;
    }

    load(part) {
        this.part = part;
        $('.img-container img', this.$panel).attr('src', this.part.image.thumbnails.large);
    }
    
    open() {
        this.opened = true;
        this.$panel.show();
    }
    
    close() {
        this.opened = false;
        this.$panel.hide();
    }
    
    toggle() {
        if (this.opened) this.close();
        else this.open();
    }
    
    reset() {}
}
