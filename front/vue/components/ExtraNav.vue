<template>
    <div class="nav-item ml-auto" id="toggle-panels">
        <button type="button"
                id="source-panel-btn"
                @click="togglePanel"
                data-target="source"
                class="open-panel nav-item btn"
                v-bind:class="[ show.source ? 'btn-primary' : 'btn-secondary' ]"
                title="Source Image"><i class="click-through fas fa-eye"></i></button>
        <button type="button"
                id="seg-panel-btn"
                @click="togglePanel"
                data-target="segmentation"
                class="open-panel nav-item btn"
                v-bind:class="[ show.segmentation ? 'btn-primary' : 'btn-secondary' ]"
                title="Segmentation"><i class="click-through fas fa-align-left"></i></button>
        <button type="button"
                id="trans-panel-btn"
                @click="togglePanel"
                data-target="visualisation"
                class="open-panel nav-item btn"
                v-bind:class="[ show.visualisation ? 'btn-primary' : 'btn-secondary' ]"
                title="Transcription"><i class="click-through fas fa-language"></i></button>
        <button type="button"
                id="diplo-panel-btn"
                @click="togglePanel"
                data-target="diplomatic"
                class="open-panel nav-item btn"
                v-bind:class="[ show.diplomatic ? 'btn-primary' : 'btn-secondary' ]"
                title="Text"><i class="click-through fas fa-list-ol"></i></button>
    </div>
</template>

<script>
export default {
    props: ['show'],
    methods: {
        togglePanel(ev)  {
            let btn = ev.target;
            let target = btn.getAttribute('data-target');
            this.show[target] = !this.show[target];
            userProfile.set(target + '-panel', this.show[target]);

            // wait for css
            Vue.nextTick(function() {
                if(this.$refs.segPanel) this.$refs.segPanel.refresh();
                if(this.$refs.visuPanel) this.$refs.visuPanel.refresh();
                if(this.$refs.diploPanel) this.$refs.diploPanel.refresh();
            }.bind(this));
        },
    }
}
</script>

<style scoped>
</style>