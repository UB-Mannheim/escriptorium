<template>
    <div class="col panel">
        <div class="tools">
            <i title="Visual Transcription Panel"
                class="panel-icon fas fa-language"></i>
        </div>
        <div class="content-container">
            <div id="visu-zoom-container" class="content">
                <svg :class="'w-100 ' + defaultTextDirection">
                    <visuline v-for="line in $store.state.lines.all"
                                ref="visulines"
                                v-bind:text-direction="defaultTextDirection"
                                v-bind:line="line"
                                v-bind:ratio="ratio"
                                v-bind:key="'VL' + line.pk">
                    </visuline>
                </svg>
            </div>
        </div>

        <TranscriptionModal v-if="editLine"
                            v-bind:line="editLine"
                            v-bind:default-text-direction="defaultTextDirection"
                            v-bind:read-direction="readDirection">
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
    props: ['readDirection', 'defaultTextDirection'],
    data() { return  {
      editLine: null
    };},
    components: {
        'visuline': VisuLine,
        TranscriptionModal,
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
        editNext() {
            let index = this.$store.state.lines.all.indexOf(this.editLine);
            if(index < this.$store.state.lines.all.length - 1) {
                this.editLine = this.$store.state.lines.all[index + 1];
            }
        },
        editPrevious() {
            let index = this.$store.state.lines.all.indexOf(this.editLine);
            if(index >= 1) {
                this.editLine = this.$store.state.lines.all[index - 1];
            }
        },
        resetLines() {
            if (this.$store.state.lines.all.length && this.$refs.visulines.length) {
                this.$refs.visulines.forEach(function(line) {
                    line.reset();
                });
            }
        },
        updateView() {
            this.$el.querySelector('svg').style.height = Math.round(this.$store.state.parts.image.size[1] * this.ratio) + 'px';
            Vue.nextTick(function() {
                this.resetLines();
            }.bind(this));
        }
    }
});
</script>

<style scoped>
</style>