RegExp.escape= function(s) {
    return s.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
};

/**** Metadata stuff ****/
$(document).ready(function() {
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
function updatePart(cardElement, data) {
    cardElement.style.opacity = 0.5;  // visual feedback for the background post
    
    var $form = $('form', cardElement);
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
}

var insert_at = function(cardElement, index) {
    var parent = document.getElementById('cards-container');
    var dropable = cardElement.previousElementSibling;
    var target = $('.js-drop', parent)[index];
    console.log('drop', index);
    parent.insertBefore(dropable, target);  // drag the dropable zone with it
    parent.insertBefore(cardElement, target);
};    

var g_dragged;  // Note: chrome doesn't understand dataTransfer very well
$(document).ready(function() {
    // create & configure dropzone
    var imageDropzone = new Dropzone('.dropzone', {
        paramName: "image"
    });
    // New card creation
    imageDropzone.on("success", function(file, data) {
        // imageDropzone.removeFile(file);
        if (data.status === 'ok') {
            var template = document.getElementById('card-template');
            var html = $(template).html();
            html = html.replace('{pk}', data.pk);
            html = html.replace('{name}', data.name);
            html = html.replace('{updateurl}', data.updateUrl);
            html = html.replace('{imgurl}', data.imgUrl);
            $('#cards-container').append(html);
        }
    });
    
    $('.js-drag').attr('draggable', true);
    $('.js-drag img').attr('draggable', false);
    
    $('#cards-container').on('dragstart', '.js-drag', function(ev) {
        ev.originalEvent.dataTransfer.setData("text/card-id", ev.target.id);
        g_dragged = ev.target.id;  // for chrome
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
    
    $('#cards-container').on('change', 'input', function(ev) {
        var card = $(ev.target).parents('.card').get(0);
        updatePart(card);
    });

    // disable dragging when over input because firefox gets confused
    $('#cards-container').on('mouseover', 'input', function(ev) {
        $(this).parents('.js-drag').attr('draggable', false);
    });
    $('#cards-container').on('mouseout', 'input', function(ev) {
        $(this).parents('.js-drag').attr('draggable', true);
    });
});


