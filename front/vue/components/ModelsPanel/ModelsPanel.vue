<template>
    <div
        v-if="data.models && data.models.length"
        class="escr-models-panel"
    >
        <details
            v-for="model in data.models"
            :key="model.pk"
            class="escr-model-details"
        >
            <summary>
                <span>{{ model.name }}</span>
                <a
                    :href="model.file"
                    aria-label="Download model file"
                >
                    <DownloadIcon />
                </a>
            </summary>
            <dl>
                <dt>Role</dt>
                <dd>{{ model.job }}</dd>
                <dt>Script</dt>
                <dd>{{ model.script || "-" }}</dd>
                <dt>Size</dt>
                <dd>{{ filesize(model.file_size) }}</dd>
                <dt>Trained from</dt>
                <dd>{{ model.parent || "-" }}</dd>
                <dt>Trained status</dt>
                <dd><component :is="trainedStatusIcon(model.training)" /></dd>
                <dt>Accuracy</dt>
                <dd>
                    {{ model.accuracy_percent ? `${model.accuracy_percent.toFixed(2)}%` : "-" }}
                </dd>
                <dt>Rights</dt>
                <dd>{{ model.rights }}</dd>
                <dt>Sharing</dt>
                <dd v-if="model.can_share">
                    <a :href="`/model/${model.pk}/rights/`">Share</a>
                </dd>
                <dd v-else>
                    -
                </dd>
            </dl>
        </details>
    </div>
    <EscrLoader
        v-else
        :loading="data.loading"
        no-data-message="No models to display."
    />
</template>
<script>
import CheckIcon from "../Icons/CheckIcon/CheckIcon.vue";
import DownloadIcon from "../Icons/DownloadIcon/DownloadIcon.vue";
import EscrLoader from "../Loader/Loader.vue";
import XIcon from "../Icons/XIcon/XIcon.vue";
import { filesizeformat } from "../../store/util/filesize";
import "./ModelsPanel.css";

export default {
    name: "EscrModelsPanel",
    components: { DownloadIcon, EscrLoader },
    props: {
        data: {
            type: Object,
            required: true,
        },
    },
    methods: {
        /**
         * Get the correct "Trained" icon (Check or X) for training status.
         */
        trainedStatusIcon(training) {
            return training === true ? XIcon : CheckIcon;
        },
        /**
         * Format the filesize similarly to how Django formats it.
         */
        filesize(bytes) {
            return filesizeformat(bytes);
        },
    }
}
</script>
