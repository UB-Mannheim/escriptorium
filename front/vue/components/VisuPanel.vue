<template>
    <div class="col panel">
        <div class="tools">
            <i title="Visual Transcription Panel"
                class="panel-icon fas fa-language"></i>
            <input id="toggle-confidence"
                   class="toggle-switch"
                   type="checkbox"
                   title="Toggle confidence visualization"
                   v-on:click="toggleConfidence"
                   v-if="hasConfidence" />
            <label for="toggle-confidence"
                   class="ml-3"
                   v-if="hasConfidence"
                   title="Show the average confidence of automatic transcription (OCR/HTR) per line"
            >
                <span>Show confidence</span>
            </label>
            <input
                type="range"
                class="custom-range"
                min="1"
                max="10"
                id="confidence-range"
                step="0.1"
                v-on:input="changeConfidenceScale"
                v-if="hasConfidence"
                v-bind:disabled="!$store.state.document.confidenceVisible"
                v-model="confidenceScale"
                title="Scale the color range for average confidence visualizations"
            >
            <label for="confidence-range"
                   class="ml-1"
                   v-if="hasConfidence">
                <span>Scale colors</span>
            </label>
        </div>
        <div class="content-container">
            <div id="visu-zoom-container" class="content">
                <svg :class="'w-100 ' + $store.state.document.defaultTextDirection">
                    <visuline v-for="line in $store.state.lines.all"
                                ref="visulines"
                                v-bind:line="line"
                                v-bind:ratio="ratio"
                                v-bind:key="'VL' + line.pk">
                    </visuline>
                </svg>
            </div>
        </div>

        <TranscriptionModal v-if="$store.state.lines.editedLine">
        </TranscriptionModal>
    </div>
</template>

<script>
/*
Visual transcription panel (or visualisation panel)
*/
import { BasePanel } from '../../src/editor/mixins.js';
import VisuLine from './VisuLine.vue';
import TranscriptionModal from './TranscriptionModal.vue';

export default Vue.extend({
    mixins: [BasePanel],
    components: {
        'visuline': VisuLine,
        TranscriptionModal,
    },
    data() {
        return {
            confidenceScale: this.$store.state.document.confidenceScale,
        }
    },
    mounted() {
        // wait for the element to be rendered
        Vue.nextTick(function() {
            this.$parent.zoom.register(this.$el.querySelector('#visu-zoom-container'),
                                       {map: true});
            this.refresh();
        }.bind(this));
    },
    methods: {
        resetLines() {
            if (this.$store.state.lines.all.length && this.$refs.visulines.length) {
                this.$refs.visulines.forEach(function(line) {
                    line.reset();
                });
            }
        },
        toggleTooltip(turnOn) {
            if (turnOn) {
                // toggle on confidence tooltips
                $('[data-toggle="tooltip"]').tooltip();
            }
            else {
                // toggle off confidence tooltips
                $('[data-toggle="tooltip"]').tooltip('dispose');
            }
        },
        toggleConfidence() {
            // use opposite of stored visibility state to toggle tooltip
            this.toggleTooltip(!this.$store.state.document.confidenceVisible);
            // toggle colorized confidence overlay
            this.$store.dispatch('document/toggleConfidence');
        },
        updateView() {
            this.$el.querySelector('svg').style.height = Math.round(this.$store.state.parts.image.size[1] * this.ratio) + 'px';
            Vue.nextTick(function() {
                this.resetLines();
            }.bind(this));
        },
        changeConfidenceScale(e) {
            this.$store.dispatch('document/scaleConfidence', e.target.value);
        }
    },
    computed: {
        hasConfidence() {
            return this.$store.state.lines.all.some(line => (
                line.currentTrans?.graphs?.length || line.currentTrans?.avg_confidence
            ))
        },
    }
});
</script>

<style scoped>
</style>
