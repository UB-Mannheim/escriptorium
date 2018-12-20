'use strict';
var zoomScale, zoomPosX, zoomPosY;

class TranscriptionLine {
    constructor (box, text, ratio) {
        this.box = box;
        this.text = text;
        this.ratio = ratio;

        var $el = $('<div class="line-box"></div>');
        this.$element = $el;
        
        $el.css({
            left: this.box[0]*ratio + 'px',
            top: this.box[1]*ratio + 'px',
            width: (this.box[2] - this.box[0])*ratio  + 'px',
            height: (this.box[3] - this.box[1])*ratio + 'px'
        });
        $el.text(this.text);
        $('#part-trans').append($el);

        $el.on('mouseover', $.proxy(function(ev) {
            var x = this.$element.position().left + this.$element.parent().position().left;
            var y = this.$element.position().top + this.$element.parent().position().top;
            $('#overlay').css({
                left: x + 'px',
                top: y + 'px',
                width: (this.box[2] - this.box[0])*ratio + 'px',
                height: (this.box[3] - this.box[1])*ratio + 'px'                
            }).show();
        }, this));
        $el.on('mouseleave', function(ev) {
            $('#overlay').hide();
        });
    }
}

$(document).ready(function() {
    var img = document.querySelector('#part-img');
    wheelzoom(img);
    img.addEventListener('wheelzoom.update', function(ev) {
        $('#part-trans').css({
            left: ev.detail.posX + 'px',
            top: ev.detail.posY + 'px',
            width: ev.detail.width + 'px',
            height: ev.detail.height + 'px',
            transform: 'scale('+ev.detail.width / ev.detail.originalWidth+')'
        });
        $('#overlay').css({
            transform: 'scale('+ev.detail.width / ev.detail.originalWidth+')'
        });
    });
});
