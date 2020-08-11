var document_images_intro = introJs();
document_images_intro.setOptions({'doneLabel', 'Next page',
steps: [
{
  element: '#nav-doc-tab',
  intro: 'Update Document description (Name, Text direction or metadata).<br>',
  position: 'bottom'
},
{
  element: '#nav-edit-tab',
  intro: 'Edit Document Part. Panels to update transcriptions, baselines and masks',
  position: 'bottom'
},
{
  element: '#nav-models-tab',
  intro: 'Handle Transcription and Segmentation models related to this document.',
  position: 'bottom'
},
{
  element: '#import-selected',
  intro: 'Import document part. <br> accepted formats : IIIF, Pagexml, Alto.',
  position: 'bottom'
},
{
  element: '#document-export',
  intro: 'Import document part. <br> accepted formats : Text, Pagexml, Alto.',
  position: 'bottom'
},
{
  element: '#train-selected',
  intro: 'Train a Segmentation or Transcription model',
  position: 'bottom'
},
{
  element: '#binarize-selected',
  intro: 'Binarize the color of selected images.',
  position: 'bottom'
},
{
  element: '#segment-selected',
  intro: 'Segment selected images.',
  position: 'bottom'
},
{
  element: '#transcribe-selected',
  intro: 'Transcribe automatically the selected images.',
  position: 'top'
},
{
  element: '#js-edit',
  intro: 'Transcribe, Segment Manually the image.',
  position: 'bottom'
},
]});

function exitonboarding() {
  $.ajax({type: 'PUT', url:'/api/users/onboarding/',
          contentType: "application/json; charset=utf-8",
          data:JSON.stringify({
            onboarding : "False",
            })

      }).done($.proxy(function(data){
                console.log("success",data)
            }, this)).fail(function(data) {
                alert(data);
            });

}
