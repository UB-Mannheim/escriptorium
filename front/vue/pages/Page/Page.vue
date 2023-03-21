<template>
    <div class="escr-body">
        <GlobalNavigation />
        <main class="escr-page">
            <EscrBreadcrumbs
                v-if="breadcrumbs?.length"
                :items="breadcrumbs"
            />
            <slot name="page-content" />
            <Alerts />
        </main>
        <EscrSidebar
            v-if="sidebarActions?.length"
            :actions="sidebarActions"
            :loading="loading"
        />
    </div>
</template>
<script>
import Alerts from "../../components/Toast/ToastGroup.vue";
import EscrBreadcrumbs from "../../components/Breadcrumbs/Breadcrumbs.vue";
import EscrSidebar from "../../components/Sidebar/Sidebar.vue";
import GlobalNavigation from "../../components/GlobalNavigation/GlobalNavigation.vue";
import "./Page.css";

export default {
    name: "EscrPage",
    components: { Alerts, EscrBreadcrumbs, EscrSidebar, GlobalNavigation },
    props: {
        breadcrumbs: {
            type: Array,
            default: () => [],
        },
        loading: {
            type: Boolean,
            default: false,
        },
        sidebarActions: {
            type: Array,
            default: () => [],
        }
    }
}
</script>
