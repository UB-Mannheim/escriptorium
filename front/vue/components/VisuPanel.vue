<template>
    <div
        id="transcription-panel"
        class="col panel"
    >
        <!-- legacy mode toolbar -->
        <div
            v-if="legacyModeEnabled"
            class="tools"
        >
            <i
                title="Visual Transcription Panel"
                class="panel-icon fas fa-language"
            />
            <input
                v-if="hasConfidence && confidenceVisible"
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

        <!-- new UI toolbar -->
        <EditorToolbar
            v-else
            panel-type="visualisation"
            :disabled="disabled"
            :panel-index="panelIndex"
        >
            <template #editor-tools-center>
                <div class="escr-editortools-paneltools">
                    <!-- transcription switcher -->
                    <TranscriptionDropdown
                        :disabled="disabled"
                    />

                    <!-- confidence visualization control -->
                    <div class="escr-confidence-control">
                        <VDropdown
                            theme="escr-tooltip-small"
                            placement="bottom"
                            :distance="8"
                            :triggers="['hover']"
                        >
                            <ToggleButton
                                color="primary"
                                :checked="confidenceVizOn"
                                :disabled="disabled || !hasConfidence"
                                :on-change="onToggleConfidence"
                            >
                                <template #button-icon>
                                    <ConfidenceIcon />
                                </template>
                            </ToggleButton>
                            <template #popper>
                                Confidence visualization
                            </template>
                        </VDropdown>
                        <VDropdown
                            placement="bottom-end"
                            theme="vertical-menu"
                            :shown="confidenceMenuOpen"
                            :triggers="[]"
                            :auto-hide="true"
                            @apply-hide="closeConfidenceMenu"
                        >
                            <EscrButton
                                class="menu-toggle"
                                color="text"
                                size="small"
                                :disabled="disabled || !hasConfidence"
                                :on-click="openConfidenceMenu"
                            >
                                <template #button-icon>
                                    <ChevronDownIcon />
                                </template>
                            </EscrButton>
                            <template #popper>
                                <div class="confidence-scale">
                                    <h3>Confidence visualization</h3>
                                    <input
                                        id="confidence-range"
                                        type="range"
                                        class="custom-range"
                                        min="1"
                                        max="10"
                                        step="0.1"
                                        @input="changeConfidenceScale"
                                    >
                                    <span class="small">
                                        Scale the color range for average confidence visualizations
                                    </span>
                                </div>
                            </template>
                        </VDropdown>
                    </div>
                </div>
            </template>
        </EditorToolbar>

        <!-- panel content -->
        <div :class="{ 'content-container': true, 'pan-active': activeTool === 'pan' }">
            <div
                id="visu-zoom-container"
                class="content"
            >
                <svg
                    ref="visu-svg"
                    :class="`w-100 ${defaultTextDirection}`"
                >
                    <VisuLine
                        v-for="line in allLines"
                        ref="visulines"
                        :key="'VL' + line.pk"
                        :legacy-mode-enabled="legacyModeEnabled"
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
import { Dropdown as VDropdown } from "floating-vue";
import { mapActions, mapState } from "vuex";
import { BasePanel } from "../../src/editor/mixins.js";
import ConfidenceIcon from "./Icons/ConfidenceIcon/ConfidenceIcon.vue";
import ChevronDownIcon from "./Icons/ChevronDownIcon/ChevronDownIcon.vue";
import EscrButton from "./Button/Button.vue";
import EditorToolbar from "./EditorToolbar/EditorToolbar.vue";
import TranscriptionDropdown from "./EditorTranscriptionDropdown/EditorTranscriptionDropdown.vue";
import VisuLine from "./VisuLine.vue";
import ToggleButton from "./ToggleButton/ToggleButton.vue";
import TranscriptionModal from "./TranscriptionModal.vue";

export default {
    name: "VisuPanel",
    components: {
        ChevronDownIcon,
        ConfidenceIcon,
        EditorToolbar,
        EscrButton,
        ToggleButton,
        TranscriptionDropdown,
        TranscriptionModal,
        VDropdown,
        VisuLine,
    },
    mixins: [BasePanel],
    data() {
        return {
            confidenceMenuOpen: false,
        }
    },
    computed: {
        ...mapState({
            activeTool: (state) => state.globalTools.activeTool,
            allLines: (state) => state.lines.all,
            confidenceScale: (state) => state.document.confidenceScale,
            confidenceVisible: (state) => state.document.confidenceVisible,
            confidenceVizOn: (state) => state.document.confidenceVizOn,
            defaultTextDirection: (state) => state.document.defaultTextDirection,
            editedLine: (state) => state.lines.editedLine,
            image: (state) => state.parts.image,
        }),
        hasConfidence() {
            return this.allLines.some((line) => (
                line.currentTrans?.graphs?.length || line.currentTrans?.avg_confidence
            ));
        },
    },
    mounted() {
        // wait for the element to be rendered
        Vue.nextTick(function() {
            this.$parent.zoom.register(this.$el.querySelector("#visu-zoom-container"),
                {map: true});
            this.refresh();
        }.bind(this));

        if (this.legacyModeEnabled && this.hasConfidence() && this.confidenceVisible) {
            $('[data-toggle="tooltip"]').tooltip();
        }
    },
    methods: {
        ...mapActions("document", ["scaleConfidence", "toggleConfidence"]),
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
        },
        /**
         * Callback to close the type select menu
         */
        closeConfidenceMenu() {
            this.confidenceMenuOpen = false;
        },
        /**
         * Callback to open the confidence menu
         */
        openConfidenceMenu() {
            this.confidenceMenuOpen = true;
        },
        /**
         * Callback to toggle the confidence viz on and off in the new UI
         */
        onToggleConfidence() {
            this.toggleConfidence();
        }
    }
}
</script>

<style scoped>
</style>
