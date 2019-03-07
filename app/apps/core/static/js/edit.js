/*
  Panel {
      open(opened)
      close()
      ev loaded()
      reset()
      opened = false
  }
*/
var API = {
    part: '/api/documents/' + DOCUMENT_ID + '/parts/{part_pk}/'
};

$(document).ready(function() {
    var panels = {
        'source': new SourcePanel($('#img-panel, #img-tools'), true),
        'binar': new BinarizationPanel($('#binar-panel, #binar-tools'), false),
        'seg': new SegmentationPanel($('#seg-panel, #seg-tools'), false),
        'trans': new TranscriptionPanel($('#trans-panel, #trans-tools'), false)
    };
    function loadPart(pk) {
        // cleanup previous page references
        var uri = API.part.replace('{part_pk}', pk);
        $.get(uri, function(data) {
            for (var key in panels) {
                panels[key].load(data);
            }

            /* previous and next button */
            window.history.pushState({},"", document.location.href.replace(/(part\/)\d+(\/edit)/, '$1'+data.pk+'$2'));
            if (data.previous) $('a#prev-part').data('target', data.previous).show();
            else $('a#prev-part').hide();
            if (data.next) $('a#next-part').data('target', data.next).show();
            else $('a#next-part').hide();
        });        
    }
    /* export */
    $('#document-export button').click(function(ev) {
        ev.preventDefault();
        var selectedTranscription = $('#document-transcriptions').val();
        var href = $('#document-export').data('href');
        var new_href = href.replace(/(transcription\/)\d+(\/export)/,
                                    '$1'+selectedTranscription+'$2');
        window.open(new_href);
    });

    $('.open-panel').on('click', function(ev) {
        $(ev.target).toggleClass('btn-primary').toggleClass('btn-secondary');
        var panel = $(ev.target).data('target');
        panels[panel].toggle();
        for (var key in panels) {
            panels[key].reset();
        }
    });
    
    $('a#prev-part, a#next-part').click(function(ev) {
        ev.preventDefault();
        var pk = $(ev.target).parents('a').data('target');
        loadPart(pk);
    });
    
    loadPart(PART_ID);
});
