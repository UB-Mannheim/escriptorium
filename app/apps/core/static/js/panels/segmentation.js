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
        this.zoomTarget = zoom.register(this.$img.get(0), {map: true});
        this.segmenter = new Segmenter(this.$img.get(0), {delayInit:true, idField:'pk'});
        this.segmenter.events.addEventListener('baseline-editor-lines-update', function(event) {
            console.log('Save ', event.detail);
        });
    }
    
    load(part) {
        super.load(part);

        if (this.part.image.thumbnails) {
            this.$img.attr('src', this.part.image.thumbnails.large);
        } else {
            this.$img.attr('src', this.part.image.uri);
        }

        function init() {
            this.segmenter.init();
            this.segmenter.load(part);
            this.bindZoom();
        }
        
        if (this.$img.complete) init.bind(this)();
        this.$img.on('load', $.proxy(function(event) {
            init.bind(this)();
        }, this));
    }

    reset() {
        super.reset();
        this.segmenter.refresh();
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
            if(e.detail.scale) {
                paper.view.scale(1/paper.view.zoom, [0, 0]);
                paper.view.scale(e.detail.scale, [0, 0]);
            }
            // paper.view.viewSize = [img.naturalWidth*zoom.scale, img.naturalHeight*zoom.scale];
            // let oldViewSize = paper.view.viewSize;
            // paper.view.viewSize = [img.naturalWidth*zoom.scale, img.naturalHeight*zoom.scale];
            // if (oldViewSize.width != paper.view.viewSize.width) {
            //     paper.view.scale(paper.view.viewSize.width/oldViewSize.width, [0, 0]);
            //     for (let i in zoom.targets) {
            //         zoom.targets[i].refreshMap();
            //     }
            // }
            this.segmenter.refresh();
        }.bind(this));
    }
}
