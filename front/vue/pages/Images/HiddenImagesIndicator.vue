<template>
    <div class="hidden-images-indicator">
        <span v-if="filteredParts.length < parts.length">
            {{ parts.length - filteredParts.length }}
            images hidden by search filter
        </span>
        <span
            v-if="hiddenSelectedCount > 0"
        >
            including {{ hiddenSelectedCount }} selected images
        </span>
        <EscrButton
            v-if="filteredParts.length < parts.length"
            label="Clear search filter"
            color="outline-secondary"
            size="small"
            :disabled="loading && loading.images"
            :on-click="onClearTextFilter"
        >
            <template #button-icon>
                <XCircleFilledIcon />
            </template>
        </EscrButton>
        <span v-if="parts.length < partsCount">
            Only the first {{ parts.length }} images currently visible;
            click "Load More" below to load more images.
        </span>
    </div>
</template>
<script>
import { mapState } from "vuex";
import EscrButton from "../../components/Button/Button.vue";
import XCircleFilledIcon from "../../components/Icons/XCircleFilledIcon/XCircleFilledIcon.vue";
export default {
    name: "EscrHiddenImagesIndicator",
    components: {
        EscrButton,
        XCircleFilledIcon,
    },
    props: {
        /**
         * Array of images visible with the search filter applied
         */
        filteredParts: {
            type: Array,
            required: true,
        },
        /**
         * Number of currently selected items that are filtered out
         */
        hiddenSelectedCount: {
            type: Number,
            required: true,
        },
        /**
         * Callback for clearing the text filter
         */
        onClearTextFilter: {
            type: Function,
            required: true,
        },
    },
    computed: {
        ...mapState({
            loading: (state) => state.images.loading,
            parts: (state) => state.document.parts,
            partsCount: (state) => state.document.partsCount,
        }),
    }
}
</script>
