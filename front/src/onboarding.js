/*
Just set ONBOARDING_PAGE in the page before the scripts block.super eg:

const ONBOARDING_PAGE = 'onboarding_document_form';

*/
export function bootOnboarding() {
    if (typeof ONBOARDING_PAGE !== 'undefined') {
        var onboarding_page_done = userProfile.get(ONBOARDING_PAGE) || false;

        if (!onboarding_page_done) {
            var intro = introJs().setOptions({'skipLabel': "Skip"});
            intro.oncomplete(function() {
                userProfile.set(ONBOARDING_PAGE, true);
            })
            intro.onbeforeexit(function(aa) {
                if (intro._currentStep<intro._introItems.length-1) {
                    if (!userProfile.get(ONBOARDING_PAGE, true)) {
                        if (confirm("Are you sure you want to avoid further help?")) {
                            exitOnboarding();
                        } else {
                            return false;
                        }
                    }
                } else {
                    userProfile.set(ONBOARDING_PAGE, true);
                }
            });

            //document_form
            if (ONBOARDING_PAGE == 'onboarding_document_form') {
                intro.setOptions({
                    steps: [
                        {
                            element: '#nav-doc-tab',
                            intro: 'Update Document description (Name, Text direction or metadata).',
                            position: 'bottom',
                        },
                        {
                            element: '#nav-img-tab',
                            intro: 'Upload images and changes their orders, import and export transcriptions, launch mass automatic segmentation or transcription.',
                            position: 'bottom',
                        },
                        {
                            element: '#nav-edit-tab',
                            intro: 'Panels to update transcriptions, baselines and masks.',
                            position: 'bottom',
                        },
                        {
                            element: '#nav-models-tab',
                            intro: 'Handle Transcription and Segmentation models related to this document.',
                            position: 'bottom'
                        },
                    ]
                });

            } else if (ONBOARDING_PAGE == 'onboarding_images') {
                intro.setOptions({
                    steps: [
                        {
                            element: '#import-selected',
                            intro: 'Import images, segmentation and/or transcriptions. <br> accepted formats : IIIF, PAGE, ALTO.',
                            position: 'bottom'
                        },
                        {
                            element: '#document-export',
                            intro: 'Export segmentation and/or transcriptions. <br> accepted formats : Text, PAGE, ALTO.',
                            position: 'bottom'
                        },
                        {
                            element: '#train-selected',
                            intro: 'Train a Segmentation or Transcription model.',
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

            } else if (ONBOARDING_PAGE == 'onboarding_edit') {
                intro.setOptions({
                    steps: [
                        // {
                        //     element: '#document-transcriptions',
                        //     intro: 'Here you can select which transcription to display. You may have several transcriptions for a given page,<br> for instance a manual one and one created automatically, or two different editions that you have imported.',
                        //     position: 'bottom',
                        // },
                        {
                            element: '#seg-panel-btn',
                            intro: 'In this panel you can manually segment the image or correct the segmentation. You can draw regions or lines onto the image, or change existing lines or regions,<br> and you can also add categories to the different regions and lines (‘main text’, ‘marginal gloss’, ‘page number’ etc.)',
                            position: 'left',
                        },
                        {
                            element: '#trans-panel-btn',
                            intro: 'In this pane you can enter or correct a transcription line-by-line.<br> Clicking on a line of text will bring up a window showing the image of that line, and a box where you can enter or correct the transcription.',
                            position: 'left',
                        },
                        {
                            element: '#diplo-panel-btn',
                            intro: 'This shows another form for entering transcription.<br> Here you can enter and work with multiple lines at a time, for instance copying and pasting a block of text from another source.\n.',
                            position: 'left',
                        },
                    ]
                });
            } else if (ONBOARDING_PAGE == 'onboarding_models') {
                intro.setOptions({
                    doneLabel: null,
                    steps: [{
                        element: '#models-table',
                        intro: 'Here you manage Transcription and Segmentation models related to this document.',
                        position: 'bottom'
                    }]
                });
            }

            document.addEventListener('DOMContentLoaded', function() {
                intro.start();
            });
        }
    }
}

function exitOnboarding() {
    $.ajax({
        type: 'PUT',
        url: '/api/user/onboarding/',
        contentType: "application/json; charset=utf-8",
        data: JSON.stringify({
            onboarding: "False",
        })
    });
}
