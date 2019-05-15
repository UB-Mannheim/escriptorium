'use strict';

class WheelZoom {
    constructor(options) {
        this.options = options || {};
        var defaults = {
            factor: 0.1,
            min_scale: 1,
            max_scale: null,
            initial_scale: 1,
            disabled: false
        };
        
        this.factor = options.factor || defaults.factor;
        this.min_scale = options.min_scale || defaults.min_scale;
        this.max_scale = options.max_scale || defaults.max_scale;
        this.initial_scale = options.initial_scale || defaults.initial_scale;
        this.disabled = options.disabled || defaults.disabled;
        
        // create a dummy tag for event bindings
        this.events = $('<div id="wheelzoom-events-js">');
        this.events.appendTo($('body'));
        
        this.targets = []; this.containers = [];
        this.previousEvent = null;
        this.scale = this.initial_scale;
        this.pos = {x:0, y:0};
    }
    
    register(container, mirror) {
        var target = container.children().first();
        this.size = {w:target.width() * this.scale, h:target.height() * this.scale};
        this.min_scale = this.options.min_scale || Math.min(
            $(window).width() / (this.size.w * this.initial_scale) * 0.9,
            $(window).height() / (this.size.h * this.initial_scale) * 0.9);
        target.css({transformOrigin: '0 0', transition: 'transform 0.3s'});
        
        if (mirror !== true) {
            target.css({cursor: 'zoom-in'});
            container.on("mousewheel DOMMouseScroll", $.proxy(this.scrolled, this));
            container.on('mousedown', $.proxy(this.draggable, this));
        } else {
            container.addClass('mirror');
        }
        this.events.on('wheelzoom.reset', $.proxy(this.reset, this));
        this.events.on('wheelzoom.refresh', $.proxy(this.refresh, this));
        
        this.targets.push(target);
        this.containers.push(container);
    }
    
	scrolled(e) {
        if (this.disabled) return;
        e.preventDefault();
		var offset = $(e.delegateTarget).closest('.img-container').offset();
		var zoom_point = {x: e.originalEvent.pageX - offset.left,
		                  y: e.originalEvent.pageY - offset.top};
		var delta = e.delta || e.originalEvent.wheelDelta;
		if (delta === undefined) {
	      //we are on firefox
	      delta = -e.originalEvent.detail;
	    }
        // cap the delta to [-1,1] for cross browser consistency
	    delta = Math.max(-1, Math.min(1, delta));
	    // determine the point on where the slide is zoomed in
 	    var zoom_target = {x: (zoom_point.x - this.pos.x) / this.scale,
	                       y: (zoom_point.y - this.pos.y) / this.scale};

	    // apply zoom
	    this.scale += delta * this.factor * this.scale;
        
	    if(this.min_scale !== null) this.scale = Math.max(this.min_scale, this.scale);
        if(this.max_scale !== null) this.scale = Math.min(this.max_scale, this.scale);

        this.pos.x = Math.round(-zoom_target.x * this.scale + zoom_point.x);
		this.pos.y = Math.round(-zoom_target.y * this.scale + zoom_point.y);

        this.updateStyle();
	}
    
	drag(e) {
        if (this.disabled) return;
		e.preventDefault();
		this.pos.x += (e.pageX - this.previousEvent.pageX);
		this.pos.y += (e.pageY - this.previousEvent.pageY);
		this.previousEvent = e;
		this.updateStyle();
	}

	removeDrag() {
        this.targets.forEach(function(e,i) {e.removeClass('notransition');});
		$(document).off('mouseup', this.removeDrag);
		$(document).off('mousemove', this.drag);
	}

	draggable(e) {
        if (this.disabled) return;
		e.preventDefault();
		this.previousEvent = e;
        // disable transition while dragging
        this.targets.forEach(function(e,i) {e.addClass('notransition');});
		$(document).on('mousemove', $.proxy(this.drag, this));
		$(document).on('mouseup', $.proxy(this.removeDrag, this));
	}
    
	updateStyle() {
	    // Make sure the slide stays in its container area when zooming in/out
        let container = this.getVisibleContainer();
        if (this.size.w*this.scale > container.width()) {
	        if(this.pos.x > 0) { this.pos.x = 0; }
	        if(this.pos.x+this.size.w*this.scale < container.width()) { this.pos.x = container.width() - this.size.w*this.scale; }
        } else {
	        if(this.pos.x < 0) { this.pos.x = 0; }
	        if(this.pos.x+this.size.w*this.scale > container.width()) { this.pos.x = container.width() - this.size.w*this.scale; }
        }

        if (this.size.h*this.scale > container.height()) {
            if(this.pos.y > 0) { this.pos.y = 0; }
	        if(this.pos.y+this.size.h*this.scale < container.height()) { this.pos.y = container.height() - this.size.h*this.scale; }
        } else {
            if(this.pos.y < 0) { this.pos.y = 0; }
            if(this.pos.y+this.size.h*this.scale > container.height()) { this.pos.y = container.height() - this.size.h*this.scale; }
        }

        
        // apply scale first for transition effect
        this.targets.forEach($.proxy(function(e, i) {
            e.css('transform', 'scale('+this.scale+')')
             .css('transform', 'translate('+(this.pos.x)+'px,'+
                  (this.pos.y)+'px) scale('+this.scale+')'); }, this));
        
        this.events.trigger('wheelzoom.updated');
	}
    
    getVisibleContainer() {
        return this.containers.find(function(e) { return e.is(':visible:not(.mirror)') && e.height() != 0;});
    }
    
    refresh() {
        let container = this.getVisibleContainer();
        var target = container.children().first();
        this.size = {w:target.width(), h:target.height()};
        this.min_scale = this.options.min_scale || Math.min(
            $(window).width() / (this.size.w * this.initial_scale) * 0.9,
            $(window).height() / (this.size.h * this.initial_scale) * 0.9);
        this.updateStyle();
    }
    
    reset() {
        let container = this.getVisibleContainer();
        this.pos = {x:0, y:0};
	    this.scale = this.initial_scale || 1;
        this.size = {w: container.width(), h: container.height()};
        this.updateStyle();
    }
    
    disable() {
        this.disabled = true;
    }

    enable() {
        this.disabled = false;
    }
    
    destroy() {
        $(this.containers).off("mousewheel DOMMouseScroll");
    }
}
