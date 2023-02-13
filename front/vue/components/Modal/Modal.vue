<template>
    <div
        class="escr-modal-backdrop"
        aria-modal="true"
    >
        <div class="escr-modal">
            <slot name="modal-content" />
            <div class="modal-actions">
                <slot name="modal-actions" />
            </div>
        </div>
    </div>
</template>
<script>
import "./Modal.css";
export default {
    name: "EscrModal",
}
</script>
