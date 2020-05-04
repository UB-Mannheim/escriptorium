var document_images_intro = introJs();
console.log("hihi");
document_images_intro.setOptions({
steps: [
{
  element: '#nav-doc-tab',
  intro: 'This guided tour will explain the Hongkiat demo page interface.<br><br>Use the arrow keys for navigation or hit ESC to exit the tour immediately.',
  position: 'bottom'
},
{
  element: '#nav-edit-tab',
  intro: 'Click this main logo to view a list of all Hongkiat demos.',
  position: 'bottom'
},
    {
  element: '#nav-models-tab',
  intro: 'Click this main logo to view a list of all Hongkiat demos.',
  position: 'bottom'
},  {
  element: '#document-image-dropzone',
  intro: 'Click this main logo to view a list of all Hongkiat demos.',
  position: 'bottom'
},
  {
  element: '#import-selected',
  intro: 'Click this main logo to view a list of all Hongkiat demos.',
  position: 'bottom'
},
  {
  element: '#document-export',
  intro: 'Click this main logo to view a list of all Hongkiat demos.',
  position: 'bottom'
},
{
  element: '#train-selected',
  intro: 'Click this main logo to view a list of all Hongkiat demos.',
  position: 'bottom'
},
{
  element: '#binarize-selected',
  intro: 'Click this main logo to view a list of all Hongkiat demos.',
  position: 'bottom'
},
{
  element: '#segment-selected',
  intro: 'Click this main logo to view a list of all Hongkiat demos.',
  position: 'bottom'
},
{
  element: '#transcribe-selected',
  intro: 'Click this main logo to view a list of all Hongkiat demos.',
  position: 'top'
},
{
  element: '#js-edit',
  intro: 'Click this main logo to view a list of all Hongkiat demos.',
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
