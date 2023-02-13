<template>
    <div class="escr-page">
        <slot name="page-content" />
        <Alerts />
    </div>
</template>
<script>
import Alerts from "../../components/Toast/ToastGroup.vue";

export default {
    name: "EscrPage",
    components: { Alerts },
}
</script>
