<template>
    <div class="row">
        <div class="col-sides">
            <a
                v-if="$store.state.document.readDirection == 'rtl' && $store.state.parts.next"
                id="next-part"
                href="#"
                class="nav-btn nav-next"
                title="Next (Page Down or Ctrl+Left Arrow)"
                @click="getNext"
            >
                <i class="fas fa-angle-left" /></a>
            <a
                v-else-if="$store.state.document.readDirection != 'rtl' && $store.state.parts.previous"
                id="prev-part"
                href="#"
                class="nav-btn nav-prev"
                title="Previous (Page Up or Ctrl+Right Arrow)"
                @click="getPrevious"
            >
                <i class="fas fa-angle-left" /></a>
            <div>
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
                v-if="visible_panels.metadata && $store.state.parts.loaded"
                id="metadata-panel"
                ref="metadataPanel"
            />
        </keep-alive>

        <keep-alive>
            <SourcePanel
                v-if="visible_panels.source && $store.state.parts.loaded"
                ref="sourcePanel"
                :fullsizeimage="fullsizeimage"
            />
        </keep-alive>


        <keep-alive>
            <SegPanel
                v-if="visible_panels.segmentation && $store.state.parts.loaded"
                id="segmentation-panel"
                ref="segPanel"
                :fullsizeimage="fullsizeimage"
            />
        </keep-alive>

        <keep-alive>
            <VisuPanel
                v-if="visible_panels.visualisation && $store.state.parts.loaded"
                id="transcription-panel"
                ref="visuPanel"
            />
        </keep-alive>

        <keep-alive>
            <DiploPanel
                v-if="visible_panels.diplomatic && $store.state.parts.loaded"
                id="diplo-panel"
                ref="diploPanel"
            />
        </keep-alive>

        <div class="col-sides">
            <a
                v-if="$store.state.document.readDirection == 'rtl' && $store.state.parts.previous"
                id="prev-part"
                href="#"
                class="nav-btn nav-prev"
                title="Previous (Page Up or Ctrl+Left Arrow)"
                @click="getPrevious"
            >
                <i class="fas fa-angle-right" />
            </a>
            <a
                v-else-if="$store.state.document.readDirection != 'rtl' && $store.state.parts.next"
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
</template>

<script>
import SourcePanel from "./SourcePanel.vue";
import SegPanel from "./SegPanel.vue";
import VisuPanel from "./VisuPanel.vue";
import DiploPanel from "./DiploPanel.vue";
import PartMetadataPanel from "./PartMetadataPanel.vue";

export default {
    components: {
        SourcePanel,
        SegPanel,
        VisuPanel,
        DiploPanel,
        PartMetadataPanel,
    },
    data: function() {
        return {
            zoom: new WheelZoom(),
            fullsizeimage: false,
        };
    },
    computed: {
        visible_panels() {
            return this.$store.state.document.visible_panels;
        },
        openedPanels() {
            return [this.visible_panels.source,
                this.visible_panels.segmentation,
                this.visible_panels.visualisation].filter((p)=>p===true);
        },
    },
    created() {
        document.addEventListener("keydown", function(event) {
            if (this.$store.state.document.blockShortcuts) return;
            if (event.keyCode == 8 && event.ctrlKey) {  // backspace
                this.zoom.reset();
            }
        }.bind(this));

        // load the full size image when we reach a scale > 1
        this.zoom.events.addEventListener("wheelzoom.updated", function(ev) {
            if (this.$store.state.parts.loaded && !this.fullsizeimage) {
                let ratio = ev.target.clientWidth / this.$store.state.parts.image.size[0];
                if (this.zoom.scale  * ratio > 1) {
                    this.prefetchImage(this.$store.state.parts.image.uri, function() {
                        this.fullsizeimage = true;
                    }.bind(this));
                }
            }
        }.bind(this));
    },
    methods: {
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
        async getPrevious(ev) {
            await this.$store.dispatch("parts/loadPart", "previous");
        },
        async getNext(ev) {
            await this.$store.dispatch("parts/loadPart", "next");
        },
    }
}
</script>

<style scoped>
</style>
