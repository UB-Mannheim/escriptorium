"use strict";

/*
 * Automatically create new rows for formsets when the last line is filled,
 * requires a parent element with the 'js-formset-row' class.
 * Also deals with switching the delete button style and hidden input value,
 * requires a hidden -DELETE input and a button with the 'js-formset-delete' class
 * and a for= attribute pointing to the input.
 */
export function setupFormSet(form) {
    // delete a row
    form.querySelectorAll(".js-formset-delete").forEach((e) =>
        e.addEventListener("mouseup", function (ev) {
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
        }),
    );

    // the browser might save the state of the delete box if its not posted
    // so we need to check its state on startup and change the button color accordingly
    var btns = document.getElementsByClassName("js-formset-delete");
    for (var i = 0; i < btns.length; i++) {
        var btn = btns.item(i);
        var input = document.getElementById(btn.attributes.for.value);
        if (input.value == "on") {
            btn.classList.add("btn-danger");
            btn.classList.remove("btn-outline-secondary");
        }
    }

    // add a formset row if we add data in the empty one
    form.addEventListener("change", function (ev) {
        // need to use closest to work with nested formsets
        let input = ev.target;
        let row = input.closest(".js-formset-row");
        if (row === null) return;
        // if it is the last row, we add a new one
        // :scope allows to only select direct children to deal with nested formsets
        let rows = row.parentNode.querySelectorAll(":scope > .js-formset-row");
        if (row == rows[rows.length - 1] && ev.target.value) {
            let prefix = input.id
                .split("-")
                .splice(0, input.id.split("-").length - 2)
                .join("-")
                .substr(3);
            let totalInput = form.querySelector(
                "#id_" + prefix + "-TOTAL_FORMS",
            );
            let total = parseInt(totalInput.value);
            totalInput.value = total + 1;
            let newRow = row.cloneNode(true);
            row.parentNode.appendChild(newRow);
            newRow.querySelectorAll("input,select").forEach((e) => {
                e.id = e.id.replace(/-\d+-(\D+$)/, "-" + total + "-$1");
                e.name = e.name.replace(/-\d+-(\D+$)/, "-" + total + "-$1");
                if (e.type != "hidden") e.value = "";
                if (e.nodeName == "SELECT")
                    e.querySelectorAll("option")[0].selected = true;
            });
        }
    });
}
