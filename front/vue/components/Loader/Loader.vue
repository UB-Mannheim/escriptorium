<template>
    <div
        v-if="loading"
        class="escr-loader-container"
    >
        <div
            class="escr-spinner"
            role="status"
        >
            <span class="sr-only">Loading...</span>
        </div>
    </div>
    <div
        v-else
        class="escr-loader-container"
    >
        {{ noDataMessage }}
    </div>
</template>
<script>
import "./Loader.css";
export default {
    name: "EscrLoader",
    props: {
        /**
         * Whether or not the data is loading.
         */
        loading: {
            type: Boolean,
            required: true,
        },
        /**
         * The message to display when there is no result to display.
         */
        noDataMessage: {
            type: String,
            required: true,
        }
    }
}
</script>
