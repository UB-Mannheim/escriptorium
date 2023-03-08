<template>
    <div class="escr-page">
        <EscrBreadcrumbs
            v-if="breadcrumbs?.length"
            :items="breadcrumbs"
        />
        <slot name="page-content" />
        <Alerts />
    </div>
</template>
<script>
import Alerts from "../../components/Toast/ToastGroup.vue";
import EscrBreadcrumbs from "../../components/Breadcrumbs/Breadcrumbs.vue";

export default {
    name: "EscrPage",
    components: { Alerts, EscrBreadcrumbs },
    props: {
        breadcrumbs: {
            type: Array,
            default: () => [],
        }
    }
}
</script>
