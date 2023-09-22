<template>
    <div
        id="transcription-panel"
        class="col panel"
    >
        <div
            v-if="legacyModeEnabled"
            class="tools"
        >
            <i
                title="Visual Transcription Panel"
                class="panel-icon fas fa-language"
            />
            <input
                v-if="hasConfidence"
                id="confidence-range"
                v-model="confidenceScale"
                type="range"
                class="custom-range ml-2"
                min="1"
                max="10"
                step="0.1"
                title="Scale the color range for average confidence visualizations"
                @input="changeConfidenceScale"
            >
        </div>
        <EditorToolbar
            v-else
            panel-type="visualisation"
            :disabled="disabled"
            :panel-index="panelIndex"
        >
            <template #editor-tools-center>
                <div class="escr-editortools-paneltools">
                    <input
                        v-if="hasConfidence"
                        id="confidence-range"
                        v-model="confidenceScale"
                        type="range"
                        class="custom-range ml-2"
                        min="1"
                        max="10"
                        step="0.1"
                        title="Scale the color range for average confidence visualizations"
                        @input="changeConfidenceScale"
                    >
                </div>
            </template>
        </EditorToolbar>
        <div :class="{ 'content-container': true, 'pan-active': activeTool === 'pan' }">
            <div
                id="visu-zoom-container"
                class="content"
            >
                <svg ref="visu-svg" :class="`w-100 ${defaultTextDirection}`">
                    <VisuLine
                        v-for="line in allLines"
                        ref="visulines"
                        :key="'VL' + line.pk"
                        :line="line"
                        :ratio="ratio"
                    />
                </svg>
            </div>
        </div>

        <TranscriptionModal v-if="editedLine" />
    </div>
</template>

<script>
/*
Visual transcription panel (or visualisation panel)
*/
import { mapActions, mapState } from "vuex";
import { BasePanel } from "../../src/editor/mixins.js";
import EditorToolbar from "./EditorToolbar/EditorToolbar.vue";
import VisuLine from "./VisuLine.vue";
import TranscriptionModal from "./TranscriptionModal.vue";

export default Vue.extend({
    components: {
        EditorToolbar,
        VisuLine,
        TranscriptionModal,
    },
    mixins: [BasePanel],
    computed: {
        ...mapState({
            activeTool: (state) => state.globalTools.activeTool,
            allLines: (state) => state.lines.all,
            confidenceScale: (state) => state.document.confidenceScale,
            confidenceVisible: (state) => state.document.confidenceVisible,
            defaultTextDirection: (state) => state.document.defaultTextDirection,
            editedLine: (state) => state.lines.editedLine,
            image: (state) => state.parts.image,
        }),
        hasConfidence() {
            return this.allLines.some((line) => (
                line.currentTrans?.graphs?.length || line.currentTrans?.avg_confidence
            )) && this.confidenceVisible
        },
    },
    mounted() {
        // wait for the element to be rendered
        Vue.nextTick(function() {
            this.$parent.zoom.register(this.$el.querySelector("#visu-zoom-container"),
                {map: true});
            this.refresh();
        }.bind(this));

        if (this.hasConfidence) {
            $('[data-toggle="tooltip"]').tooltip();
        }
    },
    methods: {
        ...mapActions("document", ["scaleConfidence"]),
        resetLines() {
            if (this.allLines.length && this.$refs.visulines.length) {
                this.$refs.visulines.forEach(function(line) {
                    line.reset();
                });
            }
        },
        updateView() {
            const svgHeight = Math.round(this.image.size[1] * this.ratio);
            this.$refs["visu-svg"].style.height = `${svgHeight}px`;
            Vue.nextTick(function() {
                this.resetLines();
            }.bind(this));
        },
        changeConfidenceScale(e) {
            this.scaleConfidence(e.target.value);
        }
    }
});
</script>

<style scoped>
</style>
