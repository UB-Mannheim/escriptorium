/*
* Usage:
* var zoom = new WheelZoom()
* zoom.register(container);
*/

'use strict';

class zoomTarget {
    constructor(domElement) {
        // wrap the element in a container:
        var container = document.createElement('div');
        container.style.position = 'relative';
        container.style.overflow = 'hidden';
        domElement.parentNode.insertBefore(container, domElement);
        container.appendChild(domElement);
        this.container = container;
        domElement.style.transformOrigin = '0 0';
        domElement.style.transition = 'transform 0.3s';
        this.element = domElement;
    }
}

class WheelZoom {
    constructor({factor=0.1,
                 minScale=0.2,
                 maxScale=null,
                 initialScale=1,
                 disabled=false}) {
        this.factor = factor;
        this.minScale = minScale;
        this.maxScale = maxScale;
        this.initialScale = initialScale;
        this.disabled = disabled;
        
        // create a dummy tag for event bindings
        this.events = document.createElement('div');
        this.events.setAttribute('id', 'wheelzoom-events-js');
        document.body.appendChild(this.events);
        
        this.targets = [];
        this.previousEvent = null;
        this.scale = this.initialScale;
        this.pos = {x:0, y:0};
    }
    
    register(domElement, {mirror=false}) {
        this.minScale = this.minScale || Math.min(
            window.width / (this.size.w * this.initialScale) * 0.9,
            window.height / (this.size.h * this.initialScale) * 0.9);
        
        this.events.addEventListener('wheelzoom.reset', this.reset.bind(this));
        this.events.addEventListener('wheelzoom.refresh', this.refresh.bind(this));

        this.size = {w:domElement.width * this.scale, h:domElement.height * this.scale};
        
        let target = new zoomTarget(domElement, this.scale, {});
        this.targets.push(target);
        if (!mirror) {
            // domElement.style.cursor = 'zoom-in';
            target.container.addEventListener('mousewheel', this.scrolled.bind(this));
            target.container.addEventListener('DOMMouseScroll', this.scrolled.bind(this)); // firefox
            target.container.addEventListener('mousedown', this.draggable.bind(this));
        } else {
            target.container.classList.add('mirror');
        }
    }
    
	scrolled(e) {
        if (this.disabled) return null;
        e.preventDefault();
        var oldScale = this.scale;
        
		var zoom_point = {x: e.pageX - e.target.offsetLeft,
		                  y: e.pageY - e.target.offsetTop};
		var delta = e.delta || e.wheelDelta;
		if (delta === undefined) {
	      //we are on firefox
	      delta = -e.detail;
	    }
        // cap the delta to [-1,1] for cross browser consistency
	    delta = Math.max(-1, Math.min(1, delta));
	    // determine the point on where the slide is zoomed in
 	    var zoom_target = {x: (zoom_point.x - this.pos.x) / this.scale,
	                       y: (zoom_point.y - this.pos.y) / this.scale};

	    // apply zoom
	    this.scale += delta * this.factor;
	    if(this.minScale !== null) this.scale = Math.max(this.minScale, this.scale);
        if(this.maxScale !== null) this.scale = Math.min(this.maxScale, this.scale);
        
        this.pos.x = Math.round(-zoom_target.x * this.scale + zoom_point.x);
		this.pos.y = Math.round(-zoom_target.y * this.scale + zoom_point.y);

        this.updateStyle();
        return this.scale / oldScale;
	}
    
	drag(e) {
        if (this.disabled) return null;
		e.preventDefault();
        var delta, oldPos={x: this.pos.x, y: this.pos.y};
        
		if (this.previousEvent) {
            this.pos.x += (e.pageX - this.previousEvent.pageX);
		    this.pos.y += (e.pageY - this.previousEvent.pageY);
        }

	    // Make sure the slide stays in its container area when zooming in/out
        if (this.scale > 1) {
	        if (this.pos.x > 0) { this.pos.x = 0; }
	        if (this.pos.x  < this.size.w - this.size.w * this.scale) {
                this.pos.x = this.size.w - this.size.w * this.scale;
            }
        } else {
	        if (this.pos.x < 0) { this.pos.x = 0; }
	        if (this.pos.x > this.size.w - this.size.w * this.scale) {
                this.pos.x = this.size.w - this.size.w * this.scale;
            }
        }
        
        if (this.scale > 1) {
            if (this.pos.y > 0) { this.pos.y = 0; }
	        if (this.pos.y < this.size.h - this.size.h * this.scale) {
                this.pos.y = this.size.h - this.size.h * this.scale;
            }
        } else {
            if (this.pos.y < 0) { this.pos.y = 0; }
            if (this.pos.y > this.size.h - this.size.h * this.scale) {
                this.pos.y = this.size.h - this.size.h * this.scale;
            }
        }
        
		this.previousEvent = e;
		this.updateStyle();
        return {
            x: (this.pos.x - oldPos.x) / this.scale,
            y: (this.pos.y - oldPos.y) / this.scale
        };
	}

	removeDrag() {
        this.targets.forEach(function(e,i) {e.removeClass('notransition');});
		document.removeEventListener('mouseup', this.removeDrag);
		document.removeEventListener('mousemove', this.drag);
        this.previousEvent = null;
	}

	draggable(e) {
        if (this.disabled) return;
		e.preventDefault();
		this.previousEvent = e;
        // disable transition while dragging
        var target = this.targets.find(t => t.element == e.target);
        target.element.classList.add('notransition');
		document.addEventListener('mousemove', this.drag.bind(this));
		document.addEventListener('mouseup', this.removeDrag.bind(this));
	}
    
	updateStyle() {        
        // apply scale first for transition effect
        this.targets.forEach(function(target, i) {
            // target.element.style.transform = 'scale('+this.scale+')';
            target.element.style.transform = 'translate('+(this.pos.x)+'px,'+ (this.pos.y)+'px) '+
                                             'scale('+this.scale+')';

        }.bind(this));
        // this.events.trigger('wheelzoom.updated');
	}
    
    getVisibleContainer() {
        return this.containers.find(function(e) { return e.is(':visible:not(.mirror)') && e.height() != 0;});
    }
    
    refresh() {
        // TODO
        // let container = this.getVisibleContainer();
        // if (!container) return;
        // var target = container.children().first();
        // this.size = {w:target.width(), h:target.height()};
        this.minScale = this.options.minScale || Math.min(
            window.width / (this.size.w * this.initialScale) * 0.9,
            window.height / (this.size.h * this.initialScale) * 0.9);
        this.updateStyle();
    }
    
    reset() {
        // TODO
        // let container = this.getVisibleContainer();
        this.pos = {x:0, y:0};
	    this.scale = this.initialScale || 1;
        // this.size = {w: container.width, h: container.height};
        this.updateStyle();
    }
    
    disable() {
        this.disabled = true;
    }

    enable() {
        this.disabled = false;
    }
    
    destroy() {
        // TODO
    }
}
