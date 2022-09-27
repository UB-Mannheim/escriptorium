<template>
    <div class="nav-item ml-auto" id="toggle-panels">
        <button type="button"
                id="meta-panel-btn"
                v-on:click="onPushPanelBtn"
                data-target="metadata"
                class="open-panel nav-item btn"
                v-bind:class="[ visible_panels.metadata ? 'btn-primary' : 'btn-secondary' ]"
                title="Text (Ctrl+5)"><i class="click-through fas fa-table"></i></button>

        <button type="button"
                id="source-panel-btn"
                v-on:click="onPushPanelBtn"
                data-target="source"
                class="open-panel nav-item btn"
                v-bind:class="[ visible_panels.source ? 'btn-primary' : 'btn-secondary' ]"
                title="Source Image (Ctrl+1)"><i class="click-through fas fa-eye"></i></button>
        <button type="button"
                id="seg-panel-btn"
                v-on:click="onPushPanelBtn"
                data-target="segmentation"
                class="open-panel nav-item btn"
                v-bind:class="[ visible_panels.segmentation ? 'btn-primary' : 'btn-secondary' ]"
                title="Segmentation (Ctrl+2)"><i class="click-through fas fa-align-left"></i></button>
        <button type="button"
                id="trans-panel-btn"
                v-on:click="onPushPanelBtn"
                data-target="visualisation"
                class="open-panel nav-item btn"
                v-bind:class="[ visible_panels.visualisation ? 'btn-primary' : 'btn-secondary' ]"
                title="Transcription (Ctrl+3)"><i class="click-through fas fa-language"></i></button>
        <button type="button"
                id="diplo-panel-btn"
                v-on:click="onPushPanelBtn"
                data-target="diplomatic"
                class="open-panel nav-item btn"
                v-bind:class="[ visible_panels.diplomatic ? 'btn-primary' : 'btn-secondary' ]"

                title="Text (Ctrl+4)"><i class="click-through fas fa-list-ol"></i></button>
    </div>
</template>

<script>
export default {
    computed: {
        visible_panels() {
            return this.$store.state.document.visible_panels;
        },
    },
    created() {
        window.addEventListener('keyup', function(ev) {
            let panels = [...document.getElementById('toggle-panels').querySelectorAll('button')].map(e=>e.dataset.target);

            if (ev.ctrlKey && ev.keyCode >=49 && ev.keyCode <=48+panels.length) {
                this.togglePanel(panels[ev.keyCode-49]);
            }
        }.bind(this));
    },
    methods: {
        togglePanel(target) {
            this.$store.dispatch('document/togglePanel', target);
        },
        onPushPanelBtn(evt) {
            this.togglePanel(evt.target.getAttribute('data-target'));
        }
    }
}
</script>

<style scoped>
</style>
