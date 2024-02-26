<template>
    <transition-group
        name="toast-group"
        tag="div"
        class="escr-toast-group"
    >
        <Toast
            v-for="toast in alerts"
            :key="toast.id"
            :action-label="toast.actionLabel"
            :action-link="toast.actionLink"
            :delay="toast.delay"
            :color="toast.color"
            :count="toast.count"
            :message="toast.message"
            :on-close="() => remove(toast)"
        />
    </transition-group>
</template>
<script>
import { mapActions, mapState } from "vuex";
import Toast from "./Toast.vue";
import "./Toast.css";

export default {
    name: "EscrToastGroup",
    components: { Toast },
    computed: {
        ...mapState({
            alerts: (state) => state.alerts.alerts,
        }),
    },
    methods: {
        ...mapActions("alerts", [
            "remove",
        ]),
    }
}
</script>
