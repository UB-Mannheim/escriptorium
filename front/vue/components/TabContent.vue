<template>
    <div>
        <EditorGlobalToolbar
            v-if="!legacyModeEnabled"
            :on-zoom-in="zoomIn"
            :on-zoom-out="zoomOut"
            :on-zoom-reset="resetZoom"
            :on-rotate="onRotate"
            :disabled="isWorking || !partsLoaded"
            :toggle-tool="toggleTool"
            :tool="activeTool"
        />
        <div class="row">
            <div class="col-sides">
                <a
                    v-if="readDirection == 'rtl' && nextPart"
                    id="next-part"
                    href="#"
                    class="nav-btn nav-next"
                    title="Next (Page Down or Ctrl+Left Arrow)"
                    @click="getNext"
                >
                    <i class="fas fa-angle-left" /></a>
                <a
                    v-else-if="readDirection != 'rtl' && prevPart"
                    id="prev-part"
                    href="#"
                    class="nav-btn nav-prev"
                    title="Previous (Page Up or Ctrl+Right Arrow)"
                    @click="getPrevious"
                >
                    <i class="fas fa-angle-left" /></a>
                <div v-if="legacyModeEnabled">
                    <button
                        id="zoom-reset"
                        class="btn btn-sm btn-info"
                        title="Reset zoom. (Ctrl+Backspace)"
                        @click="resetZoom"
                    >
                        <i class="fas fa-search" />
                    </button>

                    <button
                        id="zoom-in"
                        class="btn btn-sm btn-info mt-2"
                        title="Zoom in. (mousewheel up)"
                        @click="zoomIn"
                    >
                        <i class="fa fa-search-plus" />
                    </button>
                    <button
                        id="zoom-out"
                        class="btn btn-sm btn-info mt-1"
                        title="Zoom out. (mousewheel down)"
                        @click="zoomOut"
                    >
                        <i class="fa fa-search-minus" />
                    </button>
                </div>
            </div>

            <keep-alive>
                <PartMetadataPanel
                    v-if="visiblePanels.metadata && partsLoaded"
                    id="metadata-panel"
                    ref="metadataPanel"
                />
            </keep-alive>

            <keep-alive>
                <SourcePanel
                    v-if="visiblePanels.source && partsLoaded"
                    ref="sourcePanel"
                    :fullsizeimage="fullsizeimage"
                />
            </keep-alive>


            <keep-alive>
                <SegPanel
                    v-if="visiblePanels.segmentation && partsLoaded"
                    id="segmentation-panel"
                    ref="segPanel"
                    :fullsizeimage="fullsizeimage"
                    :legacy-mode-enabled="legacyModeEnabled"
                    :disabled="isWorking"
                />
            </keep-alive>

            <keep-alive>
                <VisuPanel
                    v-if="visiblePanels.visualisation && partsLoaded"
                    id="transcription-panel"
                    ref="visuPanel"
                />
            </keep-alive>

            <keep-alive>
                <DiploPanel
                    v-if="visiblePanels.diplomatic && partsLoaded"
                    id="diplo-panel"
                    ref="diploPanel"
                />
            </keep-alive>

            <div class="col-sides">
                <a
                    v-if="readDirection == 'rtl' && prevPart"
                    id="prev-part"
                    href="#"
                    class="nav-btn nav-prev"
                    title="Previous (Page Up or Ctrl+Left Arrow)"
                    @click="getPrevious"
                >
                    <i class="fas fa-angle-right" />
                </a>
                <a
                    v-else-if="readDirection != 'rtl' && nextPart"
                    id="next-part"
                    href="#"
                    class="nav-btn nav-next"
                    title="Next (Page Down or Ctrl+Right Arrow)"
                    @click="getNext"
                >
                    <i class="fas fa-angle-right" />
                </a>
            </div>
        </div>
    </div>
</template>

<script>
import { mapActions, mapState } from "vuex";
import EditorGlobalToolbar from "../components/EditorGlobalToolbar/EditorGlobalToolbar.vue";
import SourcePanel from "./SourcePanel.vue";
import SegPanel from "./SegPanel.vue";
import VisuPanel from "./VisuPanel.vue";
import DiploPanel from "./DiploPanel.vue";
import PartMetadataPanel from "./PartMetadataPanel.vue";

export default {
    components: {
        DiploPanel,
        EditorGlobalToolbar,
        PartMetadataPanel,
        SegPanel,
        SourcePanel,
        VisuPanel,
    },
    props: {
        /**
         * Whether or not legacy mode is enabled on this instance.
         */
        legacyModeEnabled: {
            type: Boolean,
            required: true,
        },
    },
    data: function() {
        return {
            // eslint-disable-next-line no-undef
            zoom: new WheelZoom({
                legacyModeEnabled: this.legacyModeEnabled,
                getActiveTool: this.getActiveTool,
            }),
            fullsizeimage: false,
            isWorking: false,
        };
    },
    computed: {
        ...mapState({
            activeTool: (state) => state.globalTools.activeTool,
            blockShortcuts: (state) => state.document.blockShortcuts,
            image: (state) => state.parts.image,
            nextPart: (state) => state.parts.next,
            partsLoaded: (state) => state.parts.loaded,
            prevPart: (state) => state.parts.previous,
            readDirection: (state) => state.document.readDirection,
            visiblePanels: (state) => state.document.visible_panels,
        }),
    },
    created() {
        document.addEventListener("keydown", function(event) {
            if (this.blockShortcuts) return;
            if (event.keyCode == 8 && event.ctrlKey) {  // backspace
                this.zoom.reset();
            }
        }.bind(this));

        // load the full size image when we reach a scale > 1
        this.zoom.events.addEventListener("wheelzoom.updated", function(ev) {
            if (this.partsLoaded && !this.fullsizeimage) {
                let ratio = ev.target.clientWidth / this.image.size[0];
                if (this.zoom.scale  * ratio > 1) {
                    this.prefetchImage(this.image.uri, function() {
                        this.fullsizeimage = true;
                    }.bind(this));
                }
            }
        }.bind(this));
    },
    methods: {
        ...mapActions("parts", ["loadPart", "rotate"]),
        ...mapActions("globalTools", ["toggleTool"]),
        prefetchImage(src, callback) {
            // It is the panel's responsibility to call this!
            let img = new Image();
            img.addEventListener("load", function() {
                if (callback) callback(src);
                img.remove();
            }.bind(this));
            img.src = src;
        },
        resetZoom() {
            this.zoom.reset();
        },
        zoomIn() {
            this.zoom.zoomIn();
        },
        zoomOut() {
            this.zoom.zoomOut();
        },
        async getPrevious() {
            await this.loadPart("previous");
        },
        async getNext() {
            await this.loadPart("next");
        },
        /**
         * helper method to read tool state from inside Wheelzoom
         */
        getActiveTool() {
            return this.activeTool;
        },
        /**
         * Rotate the current part by `angle` degrees
         * @param {Number} angle The angle to rotate, in degrees
         */
        async onRotate(angle) {
            try {
                this.isWorking = true;
                await this.rotate(angle);
            } catch (error) {
                this.addError(error);
            }
            this.isWorking = false;
        },
    }
}
</script>
