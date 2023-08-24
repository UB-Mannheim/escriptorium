"use strict";
export function bootAlignForm() {
    // don't allow beam size and max offset both to be non-zero
    const form = document.getElementById("process-part-form-align");
    const beamSizeField = form.querySelector("#id_beam_size");
    const maxOffsetField = form.querySelector("#id_max_offset");
    beamSizeField.addEventListener("input", (e) => {
        if (
            e.currentTarget.value &&
            e.currentTarget.value !== "" &&
            e.currentTarget.value !== "0"
        ) {
            maxOffsetField.setAttribute("disabled", "true");
            maxOffsetField.setAttribute("value", "");
            maxOffsetField.value = "";
        } else {
            maxOffsetField.removeAttribute("disabled");
        }
    });
    maxOffsetField.addEventListener("input", (e) => {
        if (
            e.currentTarget.value &&
            e.currentTarget.value !== "" &&
            e.currentTarget.value !== "0"
        ) {
            beamSizeField.setAttribute("disabled", "true");
            beamSizeField.setAttribute("value", "");
            beamSizeField.value = "";
        } else {
            beamSizeField.removeAttribute("disabled");
        }
    });
    // ensure fields re-enabled on modal close
    const reEnableFields = () => {
        maxOffsetField.removeAttribute("disabled");
        beamSizeField.removeAttribute("disabled");
    };
    form.querySelector('button[data-dismiss="modal"]').addEventListener(
        "click",
        reEnableFields,
    );
    form.querySelector('button[type="submit"]').addEventListener(
        "click",
        reEnableFields,
    );
}
