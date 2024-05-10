"use strict";

export function bootOntologyForm() {
    /*** Region/Line types ***/
    function pushType(type, name) {
        let uri = "/api/types/" + type + "/";
        return fetch(uri, {
            method: "post",
            credentials: "same-origin",
            headers: {
                "X-CSRFToken": Cookies.get("csrftoken"),
                Accept: "application/json",
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ name: name }),
        });
    }

    var submittedForm = false;
    let form = document.querySelector("#ontology-form");
    form.addEventListener("submit", (ev) => (submittedForm = true));

    function addTypeOption(parent, pk, name) {
        let checks = document.querySelectorAll(parent + " .form-check");
        let last_check = checks[checks.length - 1];
        let new_check = last_check.cloneNode(true);
        let new_input = new_check.querySelector("input");
        new_input.value = pk;
        new_input.checked = true;
        new_check.querySelector("label").textContent = name;
        last_check.after(new_check);

        // if trying to leave the page without updating show a warning
        window.addEventListener("beforeunload", function (ev) {
            if (!submittedForm) {
                var confirmationMessage =
                    "It looks like you have unsaved Types. " +
                    "If you leave before saving, your changes will be lost.";
                (ev || window.event).returnValue = confirmationMessage;
                return confirmationMessage;
            }
        });
    }

    document
        .getElementById("add-region-type-btn")
        .addEventListener("click", function (ev) {
            ev.preventDefault();
            let input = document.getElementById("add-region-type-input");
            if (input.value) {
                pushType("block", input.value)
                    .then((response) => response.json())
                    .then(function (data) {
                        addTypeOption("#region-types", data.pk, data.name);
                        input.value = ""; // empty the input for future use
                    });
            }
        });

    document
        .getElementById("add-line-type-btn")
        .addEventListener("click", function (ev) {
            ev.preventDefault();
            let input = document.getElementById("add-line-type-input");
            if (input.value) {
                pushType("line", input.value)
                    .then((response) => response.json())
                    .then(function (data) {
                        addTypeOption("#line-types", data.pk, data.name);
                        input.value = ""; // empty the input for future use
                    });
            }
        });

    document
        .getElementById("add-part-type-btn")
        .addEventListener("click", function (ev) {
            ev.preventDefault();
            let input = document.getElementById("add-part-type-input");
            if (input.value) {
                pushType("part", input.value)
                    .then((response) => response.json())
                    .then(function (data) {
                        addTypeOption("#part-types", data.pk, data.name);
                        input.value = ""; // empty the input for future use
                    });
            }
        });

    /*** Annotations ***/
    setupFormSet(document.getElementById("ontology-form"));
}
