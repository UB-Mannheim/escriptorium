"use strict";
export function bootDocumentForm(scripts) {
    setupFormSet(document.getElementById("document-form"));

    // link tabs
    var hash = window.location.hash;
    hash && $('div.nav.nav-tabs a[href="' + hash + '"]').tab("show");
    $("div.nav.nav-tabs a").click(function (e) {
        if (!$(this).is(".disabled")) {
            $(this).tab("show");
            var scrollmem = $("body").scrollTop();
            window.location.hash = this.hash;
        }
    });

    // When selecting a rtl script, select rtl read direction
    // flash shortly the read direction to tell the user when it changed
    $("#id_main_script").on("change", function (ev) {
        let dir = scripts[ev.target.value];
        if (dir == "horizontal-rl") {
            if ($("#id_read_direction").val() !== "rtl") {
                $("#id_read_direction")
                    .val("rtl")
                    .addClass("is-valid")
                    .removeClass("is-valid", 1000);
            }
        } else {
            if ($("#id_read_direction").val() !== "ltr") {
                $("#id_read_direction")
                    .val("ltr")
                    .addClass("is-valid")
                    .removeClass("is-valid", 1000);
            }
        }
    });
}
