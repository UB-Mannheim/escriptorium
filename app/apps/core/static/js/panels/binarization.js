class BinarizationPanel {
    constructor ($panel, opened) {
        this.$panel = $panel;
        this.opened = opened | false;
        this.$container = $('.img-container', this.$panel);
    }
    
    load(part) {
        this.part = part;
        
        $('.img-container img', this.$panel).on('load', $.proxy(function() {   
            zoom.register(this.$container);
        }, this));
        
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
    
    reset() {}
}
