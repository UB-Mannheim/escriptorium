class SourcePanel {
    constructor ($panel, opened) {
        this.$panel = $panel;
        this.opened = opened | false;
    }

    load(part) {
        this.part = part;
        $('.img-container img', this.$panel).attr('src', this.part.image.thumbnails.large);
        if (this.opened) this.open();
        var $container = $('.img-container', this.$panel);
        WheelZoom($container, false, 1, 1);
        $container.get(0).addEventListener('wheelzoom.update', function(ev) {
            $(':not(#img-panel) .img-container div.zoom-container').css({
                transform: 'translate('+ev.detail.translate.x+'px,'+ev.detail.translate.y+'px) scale('+ev.detail.scale+')'
            });
        });

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
        $('.img-container', this.$panel).trigger('wheelzoom.refresh');
    }
}
