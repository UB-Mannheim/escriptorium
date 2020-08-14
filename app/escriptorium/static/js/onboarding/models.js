var models_intro = introJs();
models_intro.setOptions('doneLabel', 'Next page');
models_intro.setOptions({steps: [
{
  element: '#models-table',
  intro: 'Here you manage Transcription and Segmentation models related to this document.',
  position: 'bottom'
}
]});

