class Panel {
    constructor ($panel, $tools, opened) {
        this.$panel = $panel;
        this.$tools = $tools;
        this.opened = opened | false;
        this.$container = $('.img-container', this.$panel);
    }
    
    load(part) {
        this.part = part;
	    if (this.opened) this.open();    
	}
    
    open() {
        this.opened = true;
        this.$panel.show();
        this.$tools.show();
        Cookies.set(this.$panel.attr('id'), true);
    }
    close() {
        this.opened = false;
        this.$panel.hide();
        this.$tools.hide();
        Cookies.set(this.$panel.attr('id'), false);
    }
    toggle() {
        if (this.opened) this.close();
        else this.open();
    }
    reset() {}
}
