<template>
    <div
        class="escr-modal-backdrop"
        aria-modal="true"
    >
        <div class="escr-modal">
            <div class="escr-modal-header">
                <slot name="modal-header" />
            </div>
            <div
                ref="escr-modal-content"
                class="escr-modal-content"
            >
                <slot
                    name="modal-content"
                    :scroll="onScrollContent"
                />
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
    methods: {
        onScrollContent() {
            this.$refs["escr-modal-content"].scroll({
                top: this.$refs["escr-modal-content"].scrollHeight,
                behavior: "smooth",
            });
        }
    }
}
</script>
