'use strict';

function WheelZoom(container, initial_scale, max_scale){
    var factor = 0.2;
	var target = container.children().first();
	var size = {w:target.width(), h:target.height()};
	var zoom_target = {x:0, y:0};
	var zoom_point = {x:0, y:0};
    var previousEvent;
    var disabled = false;
	target.css({transformOrigin: '0 0', transition: 'transform 0.3s'});
	target.on("mousewheel DOMMouseScroll", scrolled);
    target.on('mousedown', draggable);
    container.on('wheelzoom.reset', reset);
    container.on('wheelzoom.destroy', destroy);
    container.on('wheelzoom.disable', disable);
    container.on('wheelzoom.enable', enable);

    var api = {
        scale: initial_scale || 1,
        pos: {x:0, y:0}
    };
    
	function scrolled(e){
        e.preventDefault();
		var offset = container.offset();
    
		zoom_point.x = e.originalEvent.pageX - offset.left;
		zoom_point.y = e.originalEvent.pageY - offset.top;
		var delta = e.delta || e.originalEvent.wheelDelta;
		if (delta === undefined) {
	      //we are on firefox
	      delta = -e.originalEvent.detail;
	    }
        // cap the delta to [-1,1] for cross browser consistency
	    delta = Math.max(-1,Math.min(1,delta)); 

	    // determine the point on where the slide is zoomed in
	    zoom_target.x = (zoom_point.x - api.pos.x)/ api.scale;
	    zoom_target.y = (zoom_point.y - api.pos.y)/ api.scale;
      
	    // apply zoom
	    api.scale += delta * factor * api.scale;
	    api.scale = Math.max(1, api.scale);
        if (max_scale) {
            Math.min(max_scale, api.scale);
        }

        // calculate x and y based on zoom
	    api.pos.x = Math.round(-zoom_target.x * api.scale + zoom_point.x);
	    api.pos.y = Math.round(-zoom_target.y * api.scale + zoom_point.y);

	    updateStyle();
	}
    
	function drag(e) {
        if (disabled) return;
		e.preventDefault();
		api.pos.x += (e.pageX - previousEvent.pageX);
		api.pos.y += (e.pageY - previousEvent.pageY);
		previousEvent = e;
		updateStyle();
	}

	function removeDrag() {
		target.off('mouseup', removeDrag);
		target.off('mousemove', drag);
	}

	function draggable(e) {
		e.preventDefault();
		previousEvent = e;
		target.on('mousemove', drag);
		target.on('mouseup', removeDrag);
	}
    
	function updateStyle() {
	    // Make sure the slide stays in its container area when zooming out
	    if(api.pos.x>0) api.pos.x = 0;
	    if(api.pos.x+size.w*api.scale<size.w) api.pos.x = -size.w*(api.scale-1);
	    if(api.pos.y>0) api.pos.y = 0;
	    if(api.pos.y+size.h*api.scale<size.h) api.pos.y = -size.h*(api.scale-1);

		target.css('transform','translate('+(api.pos.x)+'px,'+(api.pos.y)+'px) scale('+api.scale+')');

        var event = new CustomEvent('wheelzoom.update', {detail: {
            scale: api.scale,
            translate: api.pos,
            originalWidth: size.w
        }});
        container.get(0).dispatchEvent(event);
	}

    function reset() {
        api.pos = {x:0, y:0};
	    api.scale = initial_scale || 1;
        size = {w: target.width(), h: target.height()};
        updateStyle();
    }

    function disable() {
        disabled = true;
    }

    function enable() {
        disabled = false;
    }
    
    function destroy() {
        target.off("mousewheel DOMMouseScroll", scrolled);
        target.off('mousedown', draggable);
        container.off('wheelzoom.reset', reset);
        container.off('wheelzoom.destroy', destroy);
        container.off('wheelzoom.disable', disable);
        container.off('wheelzoom.enable', enable);
    }

    return api;
}
