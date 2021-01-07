<template>
    <div class="col panel">
        <div class="tools">
            <i title="Source Panel" class="panel-icon fas fa-eye"></i>
            <a v-bind:href="part.image.uri" target="_blank">
                <button class="btn btn-sm btn-info ml-3 fas fa-download"
                        title="Download full size image" download></button>
            </a>
            <div class="btn-group">
                <button id="rotate-counter-clock"
                        @click="rotate(360-90)"
                        title="Rotate 90° counter-clockwise."
                        class="btn btn-sm btn-info ml-3 fas fa-undo"
                        autocomplete="off">R</button>
                <button id="rotate-clock"
                        @click="rotate(90)"
                        title="Rotate 90° clockwise."
                        class="btn btn-sm btn-info  fas fa-redo"
                        autocomplete="off">R</button>
            </div>
        </div>
        <div class="content-container">
            <div id="source-zoom-container" class="content">
                <img class="panel-img" v-bind:src="imageSrc"/>
                <div class="overlay panel-overlay">
                    <svg width="100%" height="100%">
                        <defs>
                            <mask id="source-overlay">
                                <rect width="100%"
                                        height="100%"
                                        fill="white"/>
                                <polygon points=""/>
                            </mask>
                        </defs>
                        <rect fill="grey"
                                opacity="0.5"
                                width="100%"
                                height="100%"
                                mask="url(#source-overlay)" />
                    </svg>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import BasePanel from './BasePanel.vue';

export default BasePanel.extend({
    props: ['part', 'fullsizeimage'],
    computed: {
        imageSrc() {
            let src = !this.fullsizeimage
                   && this.part.image.thumbnails.large
                   || this.part.image.uri;
            return src;
        }
    },
    mounted: function() {
        this.$parent.zoom.register(
            this.$el.querySelector('#source-zoom-container'),
            {map: true});
    },
    methods: {
        rotate(angle) {
            this.part.rotate(angle);
        }
    }
});
</script>

<style scoped>
</style>