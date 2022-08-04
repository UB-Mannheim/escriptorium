'use strict';
export function bootAlignForm() {
  // don't allow beam size and max offset both to be non-zero
  const form = document.getElementById("process-part-form-align");
  const beamSizeField = form.querySelector("#id_beam_size");
  const maxOffsetField = form.querySelector("#id_max_offset");
  beamSizeField.addEventListener("input", (e) => {
    if (e.currentTarget.value && e.currentTarget.value !== "" && e.currentTarget.value !== "0") {
      maxOffsetField.setAttribute("disabled", "true");
      maxOffsetField.setAttribute("value", "");
      maxOffsetField.value = "";
    } else {
      maxOffsetField.removeAttribute("disabled");
    }
  });
  // ensure max offset re-enabled on modal close
  const enableMaxOffset = () => maxOffsetField.removeAttribute("disabled");
  form.querySelector('button[data-dismiss="modal"]').addEventListener("click", enableMaxOffset);
  form.querySelector('input[type="submit"]').addEventListener("click", enableMaxOffset);
}
