<template>
    <div :class="classes">
        <WarningIcon
            v-if="color === 'danger'"
        />
        <InfoFilledIcon
            v-else-if="color === 'secondary'"
        />
        <span>{{ message }}</span>
    </div>
</template>
<script>
import InfoFilledIcon from "../Icons/InfoFilledIcon/InfoFilledIcon.vue";
import WarningIcon from "../Icons/WarningIcon/WarningIcon.vue";
import "./Alert.css";

export default {
    name: "EscrAlert",
    components: { InfoFilledIcon, WarningIcon },
    props: {
        color: {
            type: String,
            required: true,
            validator(value) {
                return ["secondary", "danger"].includes(value);
            },
        },
        message: {
            type: String,
            required: true,
        },
    },
    computed: {
        classes() {
            return {
                "escr-alert": true,
                [`escr-alert--${this.color}`]: true,
            };
        },
    },
}
</script>
