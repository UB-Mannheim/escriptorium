var document_intro = introJs();
document_intro.setOptions('doneLabel', 'Next page');
document_intro.setOptions({steps: [
{
   element: ".container-fluid",
   intro: 'Create your first document',
   position: 'top'
},
]});