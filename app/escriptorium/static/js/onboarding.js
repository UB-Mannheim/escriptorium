var onboarding_document  = userProfile.get('onboarding_document');
var onboarding_images  = userProfile.get('onboarding_images');
var onboarding_edit  = userProfile.get('onboarding_edit');
var onboarding_trans  = userProfile.get('onboarding_trans');
var onboarding_models  = userProfile.get('onboarding_models');

//document_form
var document_intro = introJs();
document_intro.setOptions({
    'doneLabel':'Next page',
    steps: [{
            element: '.container-fluid',
            intro: 'Update Document description (Name, Text direction or metadata).' +
                'Edit Document Part. Panels to update transcriptions, baselines and masks',
            position: 'top',
            tooltipClass: 'tooltip-large'
        },
    ]
});

//document_edit
steps_edit = [{
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
        intro: 'Here you can edit your document, by adding or correcting lines and regions, and by entering or correcting transcriptions',
        position: 'top',
    },
    {
        element: '#segmentation-panel',
        intro: 'In this pane you can manually segment the image or correct the segmentation. You can draw regions or lines onto the image, or change existing lines or regions,<br> and you can also add categories to the different regions and lines (‘main text’, ‘marginal gloss’, ‘page number’ etc.)',
        position: 'right',
    },
    {
        element: '#transcription-panel',
        intro: 'In this pane you can enter or correct a transcription line-by-line.<br> Clicking on a line of text will bring up a window showing the image of that line, and a box where you can enter or correct the transcription.',
        position: 'right',
    },
    {
        element: '#diplomatic-panel',
        intro: 'This shows another form for entering transcription.<br> Here you can enter and work with multiple lines at a time, for instance copying and pasting a block of text from another source.\n.',
        position: 'left',
    },
];

// document_images
var document_images_intro = introJs();
document_images_intro.setOptions('doneLabel', 'Next page');
document_images_intro.setOptions({
    steps: [
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
            element: "#cards-container",
            intro: 'This shows all the images for your manuscript. You can select one or multiple images for training, segmentation, transcribing, or export. Clicking on the [fas fa-edit] icon allows you to edit the segmentation and text. The [fa-align-left] icon shows you if the page has been segmented (green = yes, black = no, ‘pulsing’ green = segmentation in progress). The blue progress bar shows the amount of text that has been entered.\n',
            position: 'top'
        }
    ]
});

// models list

var models_intro = introJs();
models_intro.setOptions('doneLabel', 'Next page');
models_intro.setOptions({
    steps: [{
        element: '#models-table',
        intro: 'Here you manage Transcription and Segmentation models related to this document.',
        position: 'bottom'
    }]
});

// transcription modal


steps_trans = [{
        element: '#modal-img-container',
        intro: "This shows the transcription pane where you can enter or correct a transcription line-by-line.<br>" +
            " Clicking on a line of text will bring up a window showing the image of that line, and a box where you can enter or correct the transcription.\n",
        position: 'top'
    },
    {
        element: '#trans-input-container',
        intro: "Here you can select which transcriptions to show in the transcription pane for comparison.",
        position: 'top'
    }
];

function exitonboarding() {
   if(onboarding_document && onboarding_images && onboarding_edit && onboarding_trans && onboarding_models && onboarding_create){

       $.ajax({
        type: 'PUT',
        url: '/api/users/onboarding/',
        contentType: "application/json; charset=utf-8",
        data: JSON.stringify({
            onboarding: "False",
        })

    }).done($.proxy(function(data) {}, this)).fail(function(data) {
        alert(data);
    });

   }

}