var panels = {};
var API = {
    document: '/api/documents/' + DOCUMENT_ID,
    part: '/api/documents/' + DOCUMENT_ID + '/parts/{part_pk}/'
};

var zoom = new WheelZoom();
var undoManager = new UndoManager();

$(document).ready(function() {
    function makePanel(name, class_, visible) {
	    var title = name + '-panel';
	    var show = Cookies.get(title) && JSON.parse(Cookies.get(title));
	    panels[name] = new class_($('#'+title), $('#'+name+'-tools'), show);
	    if (show) {
	        $('#'+title+'-btn').addClass('btn-primary').removeClass('btn-secondary');
	    }
	}
	makePanel('source', SourcePanel);
	makePanel('binar', BinarizationPanel);
	makePanel('seg', SegmentationPanel);
	makePanel('trans', TranscriptionPanel);

    var current_part = null;
    
    function loadPart(pk, callback) {
        let uri = API.part.replace('{part_pk}', pk);
        $.get(uri, function(data) {
            for (var key in panels) {
                panels[key].load(data);
            }
            current_part = data;
            
            /* previous and next button */
            window.history.pushState({},"", document.location.href.replace(/(part\/)\d+(\/edit)/, '$1'+data.pk+'$2'));
            if (data.previous) $('a#prev-part').data('target', data.previous).show();
            else $('a#prev-part').hide();
            if (data.next) $('a#next-part').data('target', data.next).show();
            else $('a#next-part').hide();

            if (data.image && data.image.uri) {
                $('#part-name').html(data.title).attr('title', '<'+data.filename+'>');
            }
            
            // set the 'image' tab btn to select the corresponding image
            var tabUrl = new URL($('#images-tab-link').attr('href'), window.location.origin);
            tabUrl.searchParams.set('select', pk);
            $('#images-tab-link').attr('href', tabUrl);
            
            if (callback) callback(data);
        });
    }
    
    $('.open-panel').on('click', function(ev) {
        $(this).toggleClass('btn-primary').toggleClass('btn-secondary');
        var panel = $(this).data('target');
        panels[panel].toggle();
        for (var key in panels) {
            panels[key].refresh();
        }
        zoom.refresh();
    });
    
    // previous and next buttons
    $('a#prev-part, a#next-part').click(function(ev) {
        ev.preventDefault();
        var pk = $(this).data('target');
        loadPart(pk);
    });

    loadPart(PART_ID, function(data) {
        undoManager.clear();
    });
    
    // zoom slider
    $('#zoom-range').attr('min', zoom.minScale);
    $('#zoom-range').attr('max', zoom.maxScale);
    $('#zoom-range').val(zoom.scale);

    var fullSizeImg = document.createElement('img');
    fullSizeImg.addEventListener('load', function() {
        panels['source'].$img.attr('src', this.src);
        panels['source'].refresh();  // doesn't do anything for now but might in the future
        panels['seg'].$img.attr('src', this.src);
        panels['seg'].refresh(); // coordinates changes
    }, false);
    
    zoom.events.addEventListener('wheelzoom.updated', function(data) {
        if (zoom.scale > 1 && current_part !== null) {
            // zooming in, load the full size image if it's not done already to make sure the resolution is good enough to read stuff..
            if (!fullSizeImg.src.endsWith(current_part.image.uri)) {
                // check because load event triggers each time...
                fullSizeImg.src = current_part.image.uri;
            }
        }
        $('#zoom-range').val(zoom.scale);
    });
    
    $('#zoom-range').on('input', function(ev) {
        zoom.scale = parseFloat($(ev.target).val());
        zoom.refresh();
    });
    $('#zoom-reset').on('click', function(ev) {
        zoom.reset();
	    $('#zoom-range').val(zoom.scale);
    });
});
