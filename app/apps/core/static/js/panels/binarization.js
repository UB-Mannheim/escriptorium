class BinarizationPanel {
    constructor ($panel, opened) {
        this.$panel = $panel;
        this.opened = opened | false;
    }

    load(part) {
        this.part = part;
        if (this.part.bw_image) {
            $('.img-container img', this.$panel).attr('src', this.part.bw_image.thumbnails.large);

            var $container = $('.img-container', this.$panel);
            WheelZoom($container, false, 1, 1);
            $container.get(0).addEventListener('wheelzoom.update', function(ev) {
                $(':not(#binar-panel) .img-container div.zoom-container').css({
                    transform: 'translate('+ev.detail.translate.x+'px,'+ev.detail.translate.y+'px) scale('+ev.detail.scale+')'
                });
            });            
        } else {
            $('.img-container img', this.$panel).attr('src', '');
        }
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

    reset() {
        $('.img-container', this.$panel).trigger('wheelzoom.refresh');
    }
}
