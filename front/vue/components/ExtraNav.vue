<template>
    <div class="nav-item ml-auto" id="toggle-panels">
        <button type="button"
                id="source-panel-btn"
                v-on:click="togglePanel"
                data-target="source"
                class="open-panel nav-item btn"
                v-bind:class="[ visible_panels.source ? 'btn-primary' : 'btn-secondary' ]"
                title="Source Image"><i class="click-through fas fa-eye"></i></button>
        <button type="button"
                id="seg-panel-btn"
                v-on:click="togglePanel"
                data-target="segmentation"
                class="open-panel nav-item btn"
                v-bind:class="[ visible_panels.segmentation ? 'btn-primary' : 'btn-secondary' ]"
                title="Segmentation"><i class="click-through fas fa-align-left"></i></button>
        <button type="button"
                id="trans-panel-btn"
                v-on:click="togglePanel"
                data-target="visualisation"
                class="open-panel nav-item btn"
                v-bind:class="[ visible_panels.visualisation ? 'btn-primary' : 'btn-secondary' ]"
                title="Transcription"><i class="click-through fas fa-language"></i></button>
        <button type="button"
                id="diplo-panel-btn"
                v-on:click="togglePanel"
                data-target="diplomatic"
                class="open-panel nav-item btn"
                v-bind:class="[ visible_panels.diplomatic ? 'btn-primary' : 'btn-secondary' ]"
                title="Text"><i class="click-through fas fa-list-ol"></i></button>
    </div>
</template>

<script>
export default {
    computed: {
        visible_panels() {
            return this.$store.state.document.visible_panels;
        },
    },
    methods: {
        togglePanel(evt)  {
            this.$store.dispatch('document/togglePanel', evt.target.getAttribute('data-target'));
        },
    }
}
</script>

<style scoped>
</style>
