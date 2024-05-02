<template>
    <div class="task-metadata">
        <span
            v-if="status.length"
            :class="{
                [status]: true,
                status: true,
            }"
        >
            {{ status|workflowString }}
        </span>
        <span
            v-else
            class="status"
        >
            Not initiated
        </span>
    </div>
</template>
<script>
import ImageCard from "../../components/ImageCard/ImageCard.vue";

export default {
    name: "ImageWorkflowStatus",
    filters: {
        workflowString(val) {
            return ImageCard.filters.workflowString(val);
        }
    },
    props: {
        status: {
            type: String,
            default: "",
        }
    }
}
</script>
