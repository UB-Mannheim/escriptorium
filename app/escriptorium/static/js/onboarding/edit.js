function exitonboarding() {
  $.ajax({type: 'PUT', url:'/api/users/onboarding/',
          contentType: "application/json; charset=utf-8",
          data:JSON.stringify({
            onboarding : "False",
            })

      }).done($.proxy(function(data){
            }, this)).fail(function(data) {
                alert(data);
            });

}

steps_intro = [
{
  element: '#document-transcriptions',
  intro: 'Here you can select which transcription to display. You may have several transcriptions for a given page,<br> for instance a manual one and one created automatically, or two different editions that you have imported.\n',
  position: 'bottom',
},
{
  element: '#toggle-panels',
  intro: 'Show/hide panels',
  position: 'bottom',
},
{
    element: '#part-edit',
    intro : 'Here you can edit your document, by adding or correcting lines and regions, and by entering or correcting transcriptions',
    position: 'right',
},
{
    element: '#segmentation-panel',
    intro : 'In this pane you can manually segment the image or correct the segmentation. You can draw regions or lines onto the image, or change existing lines or regions,<br> and you can also add categories to the different regions and lines (‘main text’, ‘marginal gloss’, ‘page number’ etc.)',
    position: 'right',
},
{
    element: '#transcription-panel',
    intro : 'In this pane you can enter or correct a transcription line-by-line.<br> Clicking on a line of text will bring up a window showing the image of that line, and a box where you can enter or correct the transcription.',
    position: 'right',
},
{
    element: '#diplomatic-panel',
    intro : 'This shows another form for entering transcription.<br> Here you can enter and work with multiple lines at a time, for instance copying and pasting a block of text from another source.\n.',
    position: 'left',
},
]