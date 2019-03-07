class BinarizationPanel {
    constructor ($panel, opened, part) {
        this.$panel = $panel;
        this.opened = opened | false;
        // this.part = part;

        var $container = $('.img-container', this.$panel);
        WheelZoom($container, false, 1, 1);
        $container.get(0).addEventListener('wheelzoom.update', function(ev) {
            $(':not(#binar-panel) .img-container div.zoom-container').css({
                transform: 'translate('+ev.detail.translate.x+'px,'+ev.detail.translate.y+'px) scale('+ev.detail.scale+')'
            });
        });
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
