
/**** Metadata stuff ****/
$(document).ready(function() {
    // delete a metadata row
    $('.js-metadata-delete').click(function(ev) {
        var btn = ev.target;
        var input = document.getElementById(btn.attributes.for.value);
        if (input.value == "on") {
            btn.classList.add("btn-outline-secondary");
            btn.classList.remove("btn-danger");
            input.value = "";
        } else {
            btn.classList.add("btn-danger");
            btn.classList.remove("btn-outline-secondary");
            input.value = "on";
        }
    });

    // the browser might save the state of the delete box if its not posted
    // so we need to check its state on startup and change the button color accordingly
    var btns = document.getElementsByClassName('js-metadata-delete');
    for (var i=0; i < btns.length; i++) {
        var btn = btns.item(i);
        var input = document.getElementById(btn.attributes.for.value);
        if (input.value == "on") {
            btn.classList.add("btn-danger");
            btn.classList.remove("btn-outline-secondary");
        }
    }

    // add a formset row if we add data in the empty one
    $('.js-metadata-form').on('change', '.js-metadata-row input[type=text]', function(ev) {
        if ($(ev.target).is('.js-metadata-row:last input[type=text]')) {
            var total = parseInt($('#id_documentmetadata_set-TOTAL_FORMS').val());
            var $new = $('.js-metadata-row:first').clone();
            $new.html($new.html().replace(new RegExp('-0-', 'g'), '-'+total+'-'));
            $('input:not(#id_documentmetadata_set-0-document)', $new).removeAttr('value');
            $('select option:selected', $new).removeAttr('selected');
            $('.js-metadata-row:last').after($new);
            $('select', $new).focus();
            $('#id_documentmetadata_set-TOTAL_FORMS').val(total + 1);
        }
    });
});

/**** Image cards drag n drop stuff ****/
Dropzone.autoDiscover = false;

var g_dragged;  // Note: chrome doesn't understand dataTransfer very well
$(document).ready(function() {
    // create & configure dropzone
    var imageDropzone = new Dropzone('.dropzone', {
        paramName: "image",
        parallelUploads: 1  // ! important or the 'order' field gets duplicates
    });

    // update the underlying DocumentPart of a card
    var updatePart = function(cardElement, data) {
        cardElement.style.opacity = 0.5;  // visual feedback for the background post
        var $form = $('form.js-part-update-form', cardElement);
        if (data === undefined) { data = {}; }
        var post = {};
        $form.serializeArray().map(function(x){post[x.name] = x.value;});
        post = Object.assign({}, post, data);
        var url = $form.attr("action");
        var posting = $.post(url, post)
            .done(function(data) {
                // nothing to do since we moved it optimistically
            })
            .fail(function(xhr) {
                // fly it back
                if (data.index) { insert_at(cardElement, $(cardElement).data('previousIndex')); }
                // show errors
            })
            .always(function() {
                cardElement.style.opacity = "";
            });
    };

    // move a card visually
    var insert_at = function(cardElement, index) {
        var parent = document.getElementById('cards-container');
        var dropable = cardElement.previousElementSibling;
        var target = $('.js-drop', parent)[index];
        parent.insertBefore(dropable, target);  // drag the dropable zone with it
        parent.insertBefore(cardElement, target);
    };
    
    //************* New card creation **************
    imageDropzone.on("success", function(file, data) {
        if (data.status === 'ok') {
            var template = document.getElementById('card-template');
            var html = $(template).html();
            html = html
                .replace('{pk}', data.pk)
                .replace('{name}', data.name)
                .replace('{updateurl}', data.updateUrl)
                .replace('{deleteurl}', data.deleteUrl);
            var $new = $(html);
            $new.data('part-pk', data.pk);
            $('img', $new).attr('src', data.imgUrl);
            $('#cards-container').append($new);
        }
        // cleanup the dropzone if previews are pilling up
        if (imageDropzone.files.length > 7) {  // a bit arbitrary, depends on the screen but oh well
            for (i=0; i < imageDropzone.files.length - 7; i++) {
                if (imageDropzone.files[i].status == "success") {
                    imageDropzone.removeFile(imageDropzone.files[i]);
                }
            }
        }
    });

    //************* Card update *************
    $('#cards-container').on('change', 'input', function(ev) {
        var card = $(ev.target).parents('.card').get(0);
        updatePart(card);
    });
    
    //************* Card deletion *************
    $('#cards-container').on('submit', '.js-part-delete-form', function(ev) {
        ev.preventDefault();
        if (!confirm("Are you sure?")) { return; }
        var $form = $(this),
            url = $form.attr("action");
        var posting = $.post(url, $form.serialize())
            .done(function(data) {
                var $card = $form.parent('.card');
                $card.next('.js-drop').remove();
                $card.remove();
            })
            .fail(function(xhr) {
                console.log("damit.");
            });
    });

    //************* Card ordering *************
    $('.js-drag').attr('draggable', true);
    $('.js-drag img').attr('draggable', false);
    
    $('#cards-container').on('dragstart', '.js-drag', function(ev) {
        ev.originalEvent.dataTransfer.setData("text/card-id", ev.target.id);
        g_dragged = ev.target.id;  // chrome gets confused with dataTransfer, so we use a global
        $('.js-drop').addClass('drop-target');
    });
    
    $('#cards-container').on('dragend', '.js-drag', function(ev) {
        $('.js-drop').removeClass('drop-target');
    });
    
    $('#cards-container').on('dragover', '.js-drop', function(ev) {
        var index = $('.js-drop').index(ev.target);
        var elementId = ev.originalEvent.dataTransfer.getData("text/card-id");
        if (!elementId) { elementId = g_dragged; }  // for chrome
        var dragged_index = $('.card').index(document.getElementById(elementId));
        var isCard = ev.originalEvent.dataTransfer.types.indexOf("text/card-id") != -1;
        if (isCard && index != dragged_index && index != dragged_index + 1) {
            $(ev.target).addClass('drop-accept');
            ev.preventDefault();
        }
    });
    
    $('#cards-container').on('dragleave','.js-drop', function(ev) {
        ev.preventDefault();
        $(ev.target).removeClass('drop-accept');
    });
    
    $('#cards-container').on('drop', '.js-drop', function(ev) {
        ev.preventDefault();
        $(ev.target).removeClass('drop-accept');
        var elementId = ev.originalEvent.dataTransfer.getData("text/card-id");
        if (!elementId) { elementId = g_dragged; }  // for chrome
        var dragged = document.getElementById(elementId);
        var previous_index = $('.js-drag', '#cards-container').index(dragged);
        // store the previous index in case of error
        $(dragged).data('previousIndex', previous_index);
        
        var index = $('.js-drop', '#cards-container').index(ev.target);
        if (previous_index < index) {
            updatePart(dragged, {index: index - 1});  // because dragged card takes a room
        } else {
            updatePart(dragged, {index: index});
        }
        insert_at(dragged, index);
    });
    
    // disable dragging when over input because firefox gets confused
    $('#cards-container').on('mouseover', 'input', function(ev) {
        $(this).parents('.js-drag').attr('draggable', false);
    });
    $('#cards-container').on('mouseout', 'input', function(ev) {
        $(this).parents('.js-drag').attr('draggable', true);
    });
    
    // $('#cards-container').on('mouseover', '.js-segment', function(ev) {
    //     $(this).parents('.js-drag').attr('draggable', false);
    // });
    // $('#cards-container').on('mouseout', '.js-segment', function(ev) {
    //     $(this).parents('.js-drag').attr('draggable', true);
    // });
    $('.js-segment').click(function(ev) {
        var $link = $(ev.target), box;
        $('.line-box', '#segment-viewer').remove(); // cleanup
        $.get($link.data('lines-url'), function(data) {
            $('#segment-viewer img').attr('src', $link.data('src-img'));
            for (i=0; i<data.length; i++) {
                box = $('#box-tplt').clone();
                box.css('left', data[i][0]);
                box.css('top', data[i][1]);
                box.css('width', data[i][2] - data[i][0]);
                box.css('height', data[i][3] - data[i][1]);
                box.attr('id', '');
                box.show();
                box.appendTo('#segment-viewer');
            }
        });
    });
});


