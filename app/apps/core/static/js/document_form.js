'use strict';
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
