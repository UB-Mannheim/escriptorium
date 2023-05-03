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
        /**
         * An array of breadcrumbs objects, each strctured as follows:
         * {
         *     title: String,
         *     href?: String,
         * }
         */
        breadcrumbs: {
            type: Array,
            default: () => [],
        },
        /**
         * Boolean indicating whether or not the page is currently loading
         */
        loading: {
            type: Boolean,
            default: false,
        },
        /**
         * An array of sidebar action objects, each strctured as follows:
         * {
         *     data?: Object, // props for the panel component
         *     icon: VueComponent,
         *     key: String,  // each key must be unique
         *     label: String,
         *     panel: VueComponent,
         * }
         */
        sidebarActions: {
            type: Array,
            default: () => [],
        }
    }
}
</script>
