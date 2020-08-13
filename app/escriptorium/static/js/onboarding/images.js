var document_images_intro = introJs();
document_images_intro.setOptions('doneLabel', 'Next page');
document_images_intro.setOptions({steps: [
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
  position: 'left'
},
{
  element : "#cards-container",
  intro : 'This shows all the images for your manuscript. You can select one or multiple images for training, segmentation, transcribing, or export. Clicking on the [fas fa-edit] icon allows you to edit the segmentation and text. The [fa-align-left] icon shows you if the page has been segmented (green = yes, black = no, ‘pulsing’ green = segmentation in progress). The blue progress bar shows the amount of text that has been entered.\n',
  position : 'top'
}
]});

