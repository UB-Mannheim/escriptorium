<template>
    <div class="escr-image-grid-container">
        <div class="escr-image-grid">
            <div class="escr-grid-toolbar">
                <div class="escr-select-toggles">
                    <VDropdown
                        theme="escr-tooltip-small"
                        placement="bottom"
                        :distance="8"
                        :triggers="['hover']"
                    >
                        <EscrButton
                            :label="$gettext('Select All')"
                            size="small"
                            :disabled="allSelected || isUpdating"
                            :on-click="() => $emit('toggle-all')"
                        />
                        <template #popper>
                            {{ $gettext("Select all images in the document") }}
                        </template>
                    </VDropdown>
                    <VDropdown
                        theme="escr-tooltip-small"
                        placement="bottom"
                        :distance="8"
                        :triggers="['hover']"
                    >
                        <EscrButton
                            :label="$gettext('Select Visible')"
                            size="small"
                            color="outline-primary"
                            :disabled="allVisibleSelected || pages.length === 0 || isUpdating"
                            :on-click="() => $emit('select-visible')"
                        />
                        <template #popper>
                            {{ $gettext("Select only the images currently loaded on screen") }}
                        </template>
                    </VDropdown>
                    <EscrButton
                        :label="$gettext('Select None')"
                        color="outline-primary"
                        size="small"
                        :disabled="!hasSelections || isUpdating"
                        :on-click="() => $emit('deselect-all')"
                    />
                </div>
                <div
                    v-if="
                        document &&
                            document.transcriptions &&
                            document.transcriptions.length
                    "
                    class="escr-default-transcription"
                >
                    <label v-translate>Default transcription layer:</label>
                    <EscrDropdown
                        :options="transcriptionOptions"
                        :disabled="isUpdating"
                        :on-change="(e) => $emit('change-default', e)"
                    />
                    <EscrButton
                        :label="$gettext('Apply to selected')"
                        size="small"
                        color="outline-primary"
                        :disabled="!hasSelections"
                        :on-click="() => $emit('apply-default')"
                    />
                </div>
            </div>

            <EscrLoader
                v-if="isFetching || !pages || pages.length === 0"
                :loading="isFetching"
                :no-data-message="$gettext('No images to display.')"
            />
            <ul v-else>
                <ImageSelectCard
                    v-for="page in pages"
                    :key="page.pk"
                    :page="page"
                    :selected="checkSelected(page.pk)"
                    :available-transcriptions="document.transcriptions"
                    :default-transcription-id="defaultTranscriptionId"
                    @toggle="(p) => $emit('toggle-page', p)"
                    @update-transcription="
                        (p, t) => $emit('update-transcription', p, t)
                    "
                />
                <li
                    v-if="hasNextPage"
                    class="escr-load-more-container"
                >
                    <EscrButton
                        :label="$gettext('Load more')"
                        class="escr-load-more-btn"
                        color="outline-primary"
                        size="small"
                        :disabled="isLoadingMore"
                        :on-click="() => $emit('load-more')"
                    />
                </li>
            </ul>
        </div>

        <div
            v-if="isUpdating"
            class="images-loading-overlay"
        >
            <div
                class="escr-spinner"
                role="status"
            >
                <span class="sr-only">{{ $gettext("Updating...") }}</span>
            </div>
        </div>
    </div>
</template>

<script>
import { Dropdown as VDropdown } from "floating-vue";
import EscrButton from "../Button/Button.vue";
import EscrDropdown from "../Dropdown/Dropdown.vue";
import EscrLoader from "../Loader/Loader.vue";
import ImageSelectCard from "../ImageSelectCard/ImageSelectCard.vue";

export default {
    name: "BrowserImageGrid",
    components: {
        EscrButton,
        EscrDropdown,
        EscrLoader,
        ImageSelectCard,
        VDropdown,
    },
    props: {
        /**
         * The document that the DocumentParts belong to
         */
        document: {
            type: Object,
            default: null,
        },
        /**
         * The DocumentParts to be displayed
         */
        pages: {
            type: Array,
            default: () => [],
        },
        /**
         * True if DocumentParts are being fetched from the backend
         */
        isFetching: {
            type: Boolean,
            default: false,
        },
        /**
         * True if selection is being updated in a way that requires backend calls
         */
        isUpdating: {
            type: Boolean,
            default: false,
        },
        /**
         * True if the user has clicked "load more" and the DocumentParts are still loading
         */
        isLoadingMore: {
            type: Boolean,
            default: false,
        },
        /**
         * True if there is an additional page of DocumentParts
         */
        hasNextPage: {
            type: Boolean,
            default: false,
        },
        /**
         * True if all DocumentParts are selected
         */
        allSelected: {
            type: Boolean,
            default: false,
        },
        /**
         * True if any DocumentParts are selected
         */
        hasSelections: {
            type: Boolean,
            default: false,
        },
        /**
         * The list of dropdown options for default transcriptions
         */
        transcriptionOptions: {
            type: Array,
            default: () => [],
        },
        /**
         * The ID of the current default transcription
         */
        defaultTranscriptionId: {
            type: [Number, String],
            default: null,
        },
        /**
         * Callback that should return true if the passed DocumentPart pk is
         * currently staged in the collection store
         */
        checkSelected: {
            type: Function,
            required: true,
        },
    },
    computed: {
        /**
         * Returns true if every single image currently rendered in the `pages`
         * array has been selected by the user.
         */
        allVisibleSelected() {
            if (!this.pages || this.pages.length === 0) {
                return false;
            }
            return this.pages.every((page) => this.checkSelected(page.pk));
        },
    },
};
</script>
