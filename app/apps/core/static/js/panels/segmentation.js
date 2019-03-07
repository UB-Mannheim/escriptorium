class SegmentationPanel {
    constructor ($panel, opened, part) {
        this.$panel = $panel;
        this.opened = opened | false;
        // this.part = part;
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
