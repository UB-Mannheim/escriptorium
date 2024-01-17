<template>
    <div class="col panel">
        <div class="tools">
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
        <div class="content-container">
            <div
                id="visu-zoom-container"
                class="content"
            >
                <svg :class="'w-100 ' + $store.state.document.defaultTextDirection">
                    <visuline
                        v-for="line in $store.state.lines.all"
                        ref="visulines"
                        :key="'VL' + line.pk"
                        :line="line"
                        :ratio="ratio"
                    />
                </svg>
            </div>
        </div>

        <TranscriptionModal v-if="$store.state.lines.editedLine" />
    </div>
</template>

<script>
/*
Visual transcription panel (or visualisation panel)
*/
import { BasePanel } from "../../src/editor/mixins.js";
import VisuLine from "./VisuLine.vue";
import TranscriptionModal from "./TranscriptionModal.vue";

export default Vue.extend({
    components: {
        "visuline": VisuLine,
        TranscriptionModal,
    },
    mixins: [BasePanel],
    data() {
        return {
            confidenceScale: this.$store.state.document.confidenceScale,
        }
    },
    computed: {
        hasConfidence() {
            return this.$store.state.lines.all.some((line) => (
                line.currentTrans?.graphs?.length || line.currentTrans?.avg_confidence
            )) && this.$store.state.document.confidenceVisible
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
        resetLines() {
            if (this.$store.state.lines.all.length && this.$refs.visulines.length) {
                this.$refs.visulines.forEach(function(line) {
                    line.reset();
                });
            }
        },
        updateView() {
            this.$el.querySelector("svg").style.height = Math.round(this.$store.state.parts.image.size[1] * this.ratio) + "px";
            Vue.nextTick(function() {
                this.resetLines();
            }.bind(this));
        },
        changeConfidenceScale(e) {
            this.$store.dispatch("document/scaleConfidence", e.target.value);
        }
    }
});
</script>

<style scoped>
</style>
