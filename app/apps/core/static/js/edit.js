/*
  Panel {
      open(opened)
      close()
      load(part)
      reset()
  }
*/
var panels;
var API = {
    part: '/api/documents/' + DOCUMENT_ID + '/parts/{part_pk}/'
};

$(document).ready(function() {
    var show_img = JSON.parse(Cookies.get('img-panel-open') || 'true');
    var show_binar = JSON.parse(document.location.hash == '#bin' ||
                                Cookies.get('binar-panel-open') || 'false');
    var show_seg = JSON.parse(document.location.hash == '#seg' ||
                              Cookies.get('seg-panel-open') || 'false');
    var show_trans = JSON.parse(document.location.hash == '#trans' ||
                                Cookies.get('trans-panel-open') || 'false');
    panels = {
        'source': new SourcePanel($('#img-panel, #img-tools'), show_img),
        'binar': new BinarizationPanel($('#binar-panel, #binar-tools'), show_binar),
        'seg': new SegmentationPanel($('#seg-panel, #seg-tools'), show_seg),
        'trans': new TranscriptionPanel($('#trans-panel, #trans-tools'), show_trans)
    };
    if (show_img) $('#img-panel-btn').addClass('btn-primary').removeClass('btn-secondary');
    if (show_binar) $('#binar-panel-btn').addClass('btn-primary').removeClass('btn-secondary');
    if (show_seg) $('#seg-panel-btn').addClass('btn-primary').removeClass('btn-secondary');
    if (show_trans) $('#trans-panel-btn').addClass('btn-primary').removeClass('btn-secondary');
    
    function loadPart(pk) {
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
    $('button#document-export').click(function(ev) {
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
