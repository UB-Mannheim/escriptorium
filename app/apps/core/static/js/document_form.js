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

    // add region/line types

    function pushType(type, name) {
        let uri = '/api/types/'+type+'/';
        return fetch(uri, {
            method: "post",
            credentials: "same-origin",
            headers: {
                "X-CSRFToken": Cookies.get("csrftoken"),
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({name: name})
        });
    }

    function addTypeOption(parent, pk, name) {
        let checks = document.querySelectorAll(parent + " .form-check");
        let last_check = checks[checks.length-1];
        let new_check = last_check.cloneNode(true);
        let new_input = new_check.querySelector("input");
        new_input.value = pk;
        new_input.checked = true;
        new_check.querySelector("label").textContent = name;
        last_check.after(new_check);

    }

    document.getElementById("add-region-type-btn").addEventListener("click", function(ev) {
        ev.preventDefault();
        let input = document.getElementById("add-region-type-input");
        if (input.value) {
            pushType('block', input.value)
                .then((response) => response.json())
                .then(function (data) {
                    addTypeOption('#region-types', data.pk, data.name);
                    input.value = '';  // empty the input for future use
                });
        }
    });

    document.getElementById("add-line-type-btn").addEventListener("click", function(ev) {
        ev.preventDefault();
        let input = document.getElementById("add-line-type-input");
        if (input.value) {
            pushType('line', input.value)
                .then((response) => response.json())
                .then(function (data) {
                    addTypeOption('#line-types', data.pk, data.name);
                    input.value = '';  // empty the input for future use
                });
        }
    });

    // link tabs
    var hash = window.location.hash;
    hash && $('div.nav.nav-tabs a[href="' + hash + '"]').tab('show');
    $('div.nav.nav-tabs a').click(function (e) {
        if (!$(this).is('.disabled')) {
            $(this).tab('show');
            var scrollmem = $('body').scrollTop();
            window.location.hash = this.hash;
        }
    });
});
