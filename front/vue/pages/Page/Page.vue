<template>
    <div class="escr-body escr-vue-enabled">
        <div class="escr-page">
            <EscrBreadcrumbs
                v-if="breadcrumbs && breadcrumbs.length"
                :items="breadcrumbs"
            />
            <slot name="page-content" />
            <Alerts />
        </div>
        <EscrSidebar
            v-if="sidebarActions && sidebarActions.length"
            :actions="sidebarActions"
            :loading="loading"
        />
    </div>
</template>
<script>
import ReconnectingWebSocket from "reconnectingwebsocket";
import { mapActions } from "vuex";
import Alerts from "../../components/Toast/ToastGroup.vue";
import EscrBreadcrumbs from "../../components/Breadcrumbs/Breadcrumbs.vue";
import EscrSidebar from "../../components/Sidebar/Sidebar.vue";

export default {
    name: "EscrPage",
    components: { Alerts, EscrBreadcrumbs, EscrSidebar },
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
    },
    created() {
        const scheme = location.protocol === "https:" ? "wss:" : "ws:";
        const msgSocket = new ReconnectingWebSocket(`${scheme}//${window.location.host}/ws/notif/`);
        msgSocket.maxReconnectAttempts = 3;
        msgSocket.addEventListener("message", this.websocketListener);
    },
    methods: {
        ...mapActions("alerts", ["add"]),
        websocketListener(e) {
            const data = JSON.parse(e.data);
            // only handle "message" type here, for display purposes
            if (data.type == "message") {
                const message = data.text;
                // map color to our color scheme
                let color = "text";
                const colorMap = {
                    danger: "alert",
                    success: "success",
                };
                if (Object.keys(colorMap).includes(data.level)) {
                    color = colorMap[data.level];
                }
                // add links if necessary
                if (data.links && data.links.length) {
                    const actionLink = data.links[0].src;
                    const actionLabel = data.links[0].text;
                    this.add({ color, message, actionLink, actionLabel, delay: 60000 });
                } else {
                    this.add({ color, message });
                }
            }
        },
    },
}
</script>

<style scoped>
    @import "./Page.css";
</style>
