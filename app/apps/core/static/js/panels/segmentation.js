/*
TODO:
- integration
- help

- list of regions / lines (?)

*/

class SegmentationPanel extends Panel {
    constructor ($panel, $tools, opened) {
        super($panel, $tools, opened);
        this.seeBlocks = true;
        this.seeLines = true;
        this.$img = $('img', this.$container);
        
        zoom.register(this.$img.get(0));
        this.segmenter = new Segmenter(this.$img.get(0), {delayInit:true});
    }
    
    load(part) {
        super.load(part);

        if (this.part.image.thumbnails) {
            this.$img.attr('src', this.part.image.thumbnails.large);
        } else {
            this.$img.attr('src', this.part.image.uri);
        }
        if (this.$img.complete) {
            this.segmenter.init();
            this.segmenter.load(part);
            this.bindZoom();
        }
        this.$img.on('load', $.proxy(function(event) {
            this.segmenter.init();
            this.segmenter.load(part);
            this.bindZoom();
        }, this));
    }
    
    reset() {
        super.reset();
    }

    bindZoom() {
        // simulates wheelzoom for canvas
        var img = this.$img.get(0);
        zoom.events.addEventListener('wheelzoom.updated', function(e) {
            this.segmenter.deletePointBtn.style.display = 'none';
            this.segmenter.canvas.style.top = zoom.pos.y + 'px';
            this.segmenter.canvas.style.left = zoom.pos.x + 'px';
            this.segmenter.canvas.style.width = img.width*zoom.scale + 'px';
            this.segmenter.canvas.style.height = img.height*zoom.scale + 'px';
            
            let oldViewSize = paper.view.viewSize;            
            
            paper.view.viewSize = [img.width*zoom.scale, img.height*zoom.scale];
            if (oldViewSize.width != paper.view.viewSize.width) {
                paper.view.scale(paper.view.viewSize.width/oldViewSize.width, [0, 0]);
            }
        }.bind(this));
    }
}
