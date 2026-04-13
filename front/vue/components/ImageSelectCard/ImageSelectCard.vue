<template>
    <li class="escr-card-container escr-image-select-card">
        <div
            :class="{
                'escr-image-card': true,
                'image-selected': selected,
            }"
            dir="ltr"
            @click="$emit('toggle', page)"
        >
            <div class="img">
                <img
                    :src="page.thumbnail"
                    :alt="page.title || 'Page Thumbnail'"
                >
            </div>

            <label
                :for="`select-${page.pk}`"
                class="image-checkbox"
                @click.prevent.stop="$emit('toggle', page)"
            >
                <input
                    :id="`select-${page.pk}`"
                    type="checkbox"
                    class="sr-only"
                    :checked="selected"
                    readonly
                >
                <CheckCircleFilledIcon aria-hidden="true" />
                <span aria-hidden="true" />
            </label>

            <span class="element-number">{{ page.order + 1 }}</span>

            <!-- filename with tooltip for overflow -->
            <VDropdown
                placement="bottom"
                :triggers="['hover']"
                theme="escr-tooltip-small"
                class="filename"
            >
                <span>{{ page.name || page.filename || page.title || `Page ${page.pk}` }}</span>
                <template #popper>
                    {{ page.name || page.filename || page.title || `Page ${page.pk}` }}
                </template>
            </VDropdown>

            <div
                v-if="availableTranscriptions && availableTranscriptions.length"
                class="escr-card-transcription-select"
                @click.stop
            >
                <select
                    :value="
                        currentTranscriptionId || currentDefaultTranscriptionId
                    "
                    :disabled="!selected"
                    @change="
                        (e) =>
                            $emit('update-transcription', page, e.target.value)
                    "
                >
                    <option
                        v-for="t in availableTranscriptions"
                        :key="t.id || t.pk"
                        :value="t.id || t.pk"
                    >
                        {{ t.name }}
                    </option>
                </select>
            </div>
        </div>
    </li>
</template>

<script>
import { mapState } from "vuex";
import { Dropdown as VDropdown } from "floating-vue";
import CheckCircleFilledIcon from "../Icons/CheckCircleFilledIcon/CheckCircleFilledIcon.vue";
import "../ImageCard/ImageCard.css";
import "./ImageSelectCard.css";

export default {
    name: "ImageSelectCard",
    components: {
        CheckCircleFilledIcon,
        VDropdown
    },
    props: {
        page: { type: Object, required: true },
        selected: { type: Boolean, default: false },
        availableTranscriptions: { type: Array, default: () => [] },
        defaultTranscriptionId: { type: [Number, String], default: null },
    },
    computed: {
        ...mapState("collection", {
            collectionItems: (state) => state.currentCollection.items,
        }),
        /**
         * look up this part's currently selected transcription in the collection store
         */
        currentTranscriptionId() {
            const collectionItem = this.collectionItems.find(
                (item) => item.document_part === this.page.pk,
            );
            return collectionItem ? collectionItem.transcription_layer : null;
        },
        /**
         * choose manual by default
         */
        currentDefaultTranscriptionId() {
            if (this.defaultTranscriptionId) {
                return this.defaultTranscriptionId;
            }
            const avail = this.availableTranscriptions;
            if (!avail?.length) {
                return "";
            }
            const manual = avail.find((t) => t.name === "manual");
            return manual ? manual.id || manual.pk : avail[0].id || avail[0].pk;
        },
    },
};
</script>
