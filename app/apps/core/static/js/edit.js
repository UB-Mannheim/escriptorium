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
    API.part = API.part.replace('{part_pk}', PART_ID);
    $.get(API.part, function(data) {
        var panels = {
            'source': new SourcePanel($('#img-panel, #img-tools'), true, data),
            'binar': new BinarizationPanel($('#binar-panel, #binar-tools'), false, data),
            'seg': new SegmentationPanel($('#seg-panel, #seg-tools'), false, data),
            'trans': new TranscriptionPanel($('#trans-panel, #trans-tools'), false, data)
        };

        $('.open-panel').click(function(ev) {
            $(ev.target).toggleClass('btn-primary').toggleClass('btn-secondary');
            var panel = $(ev.target).data('target');
            panels[panel].toggle();
            for (var key in panels) {
                panels[key].reset();
            }
        });
    });
    
    $('#document-export button').click(function(ev) {
        ev.preventDefault();
        var selectedTranscription = $('#document-transcriptions').val();
        var href = $('#document-export').data('href');
        var new_href = href.replace(/(transcription\/)\d+(\/export)/,
                                    '$1'+selectedTranscription+'$2');
        window.open(new_href);
    });
});
