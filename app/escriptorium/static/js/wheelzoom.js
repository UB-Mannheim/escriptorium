'use strict';

function ScrollZoom(container, max_scale){
    var factor = 0.2;
	var target = container.children().first();
	var size = {w:target.width(),h:target.height()};
	var pos = {x:0,y:0};
	var zoom_target = {x:0,y:0};
	var zoom_point = {x:0,y:0};
	var scale = 1;
    var previousEvent;
	target.css('transform-origin','0 0');
	target.on("mousewheel DOMMouseScroll", scrolled);
    target.on('mousedown', draggable);

	function scrolled(e){
		var offset = container.offset();
    
		zoom_point.x = e.originalEvent.pageX - offset.left;
		zoom_point.y = e.originalEvent.pageY - offset.top;
		e.preventDefault();
		var delta = e.delta || e.originalEvent.wheelDelta;
		if (delta === undefined) {
	      //we are on firefox
	      delta = -e.originalEvent.detail;
	    }
	    delta = Math.max(-1,Math.min(1,delta)); // cap the delta to [-1,1] for cross browser consistency

	    // determine the point on where the slide is zoomed in
	    zoom_target.x = (zoom_point.x - pos.x)/scale;
	    zoom_target.y = (zoom_point.y - pos.y)/scale;
      
	    // apply zoom
	    scale += delta * factor * scale;
	    scale = Math.max(1, scale);
        if (max_scale) {
            Math.min(max_scale, scale);
        }

	    // calculate x and y based on zoom
	    pos.x = -zoom_target.x * scale + zoom_point.x;
	    pos.y = -zoom_target.y * scale + zoom_point.y;

	    updateStyle();
	}

	function drag(e) {
		e.preventDefault();
		pos.x += (e.pageX - previousEvent.pageX);
		pos.y += (e.pageY - previousEvent.pageY);
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
    
	function updateStyle(){
	    // Make sure the slide stays in its container area when zooming out
	    if(pos.x>0) pos.x = 0;
	    if(pos.x+size.w*scale<size.w) pos.x = -size.w*(scale-1);
	    if(pos.y>0) pos.y = 0;
	    if(pos.y+size.h*scale<size.h) pos.y = -size.h*(scale-1);
        
		target.css('transform','translate('+(pos.x)+'px,'+(pos.y)+'px) scale('+scale+')');

        container.get(0).dispatchEvent(new CustomEvent('wheelzoom', {detail: {
            scale: scale,
            translate: pos,
            originalWidth: size.w
        }}));
	}
}
