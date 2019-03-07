'use strict';

function WheelZoom(container, disabled_, initial_scale, min_scale_opt, max_scale_opt) {
    var factor = 0.2;
	var target = container.children().first();
    initial_scale = initial_scale || 1;
	var size = {w:target.width() * initial_scale, h:target.height() * initial_scale};
	var zoom_target = {x:0, y:0};
	var zoom_point = {x:0, y:0};
    var previousEvent;
    var disabled = disabled_;
	target.css({transformOrigin: '0 0', transition: 'transform 0.3s', cursor: 'zoom-in'});
	container.on("mousewheel DOMMouseScroll", scrolled);
    container.on('mousedown', draggable);
    container.on('wheelzoom.reset', reset);
    container.on('wheelzoom.refresh', refresh);
    container.on('wheelzoom.destroy', destroy);
    container.on('wheelzoom.disable', disable);
    container.on('wheelzoom.enable', enable);

    var api = {
        min_scale: min_scale_opt || Math.min(
            $(window).width() / target.width() * initial_scale * 0.9,
            $(window).height() / target.height() * initial_scale * 0.9),
        max_scale: max_scale_opt || 10,
        scale: initial_scale,
        pos: {x:0, y:0}
    };

	function scrolled(e){
        if (disabled) return;
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
	    delta = Math.max(-1, Math.min(1, delta));
	    // determine the point on where the slide is zoomed in
	    zoom_target.x = (zoom_point.x - api.pos.x)/ api.scale;
	    zoom_target.y = (zoom_point.y - api.pos.y)/ api.scale;
	    // apply zoom
	    api.scale += delta * factor * api.scale;
        
	    api.scale = Math.max(api.min_scale, api.scale);
        api.scale = Math.min(api.max_scale, api.scale);

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
        target.removeClass('notransition');
		container.off('mouseup', removeDrag);
		container.off('mousemove', drag);
	}

	function draggable(e) {
        if (disabled) return;
		e.preventDefault();
		previousEvent = e;
        // disable transition while dragging
        target.addClass('notransition');
		container.on('mousemove', drag);
		container.on('mouseup', removeDrag);
	}
    
	function updateStyle() {
	    // Make sure the slide stays in its container area when zooming in/out
        if (api.scale > 1) {
	        if(api.pos.x > 0) { api.pos.x = 0; }
	        if(api.pos.x+size.w*api.scale < container.width()) { api.pos.x = -size.w*(api.scale-1); }
            if(api.pos.y > 0) { api.pos.y = 0; }
	        if(api.pos.y+size.h*api.scale < container.height()) { api.pos.y = container.height() - size.h*api.scale; }
        } else {
	        if(api.pos.x < 0) { api.pos.x = 0; }
	        if(api.pos.x+size.w*api.scale > container.width()) { api.pos.x = -size.w*(api.scale-1); }
            if(api.pos.y > 0) { api.pos.y = 0; }
            if(size.h*api.scale <= container.height() && api.pos.y < 0) { api.pos.y = 0; }
	        if(size.h*api.scale >= container.height() && api.pos.y+size.h*api.scale < container.height()) { api.pos.y = container.height() - size.h*api.scale; }
            if(size.h*api.scale <= container.height() && api.pos.y+size.h*api.scale > container.height()) { api.pos.y = container.height() - size.h*api.scale; }
        }
          
        // apply scale first for transition effect
        target.css('transform','scale('+api.scale+')');
		target.css('transform','translate('+(api.pos.x)+'px,'+(api.pos.y)+'px) scale('+api.scale+')');

        var event = new CustomEvent('wheelzoom.update', {detail: {
            scale: api.scale,
            translate: api.pos,
            originalWidth: size.w
        }});
        container.get(0).dispatchEvent(event);
	}

    function refresh() {
        size = {w: target.width(), h: target.height()};
        api.min_scale = min_scale_opt || Math.min(
            $(window).width() / (size.w * initial_scale) * 0.9,
            $(window).height() / (size.h * initial_scale) * 0.9);
        updateStyle();
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
        container.off("mousewheel DOMMouseScroll", scrolled);
        container.off('mousedown', draggable);
        container.off('wheelzoom.reset', reset);
        container.off('wheelzoom.refresh', refresh);
        container.off('wheelzoom.destroy', destroy);
        container.off('wheelzoom.disable', disable);
        container.off('wheelzoom.enable', enable);
    }

    return api;
}
