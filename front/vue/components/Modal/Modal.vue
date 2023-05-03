<template>
    <div
        class="escr-modal-backdrop"
        aria-modal="true"
    >
        <div class="escr-modal">
            <div class="escr-modal-header">
                <slot name="modal-header" />
            </div>
            <div class="escr-modal-content">
                <slot name="modal-content" />
            </div>
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
