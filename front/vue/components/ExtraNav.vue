<template>
    <div
        id="toggle-panels"
        class="nav-item ml-auto"
    >
        <button
            id="meta-panel-btn"
            type="button"
            data-target="metadata"
            class="open-panel nav-item btn"
            :class="[ visible_panels.metadata ? 'btn-primary' : 'btn-secondary' ]"
            title="Metadata (Ctrl+1)"
            @click="onPushPanelBtn"
        >
            <i class="click-through fas fa-table" />
        </button>

        <button
            id="source-panel-btn"
            type="button"
            data-target="source"
            class="open-panel nav-item btn"
            :class="[ visible_panels.source ? 'btn-primary' : 'btn-secondary' ]"
            title="Source Image (Ctrl+2)"
            @click="onPushPanelBtn"
        >
            <i class="click-through fas fa-eye" />
        </button>
        <button
            id="seg-panel-btn"
            type="button"
            data-target="segmentation"
            class="open-panel nav-item btn"
            :class="[ visible_panels.segmentation ? 'btn-primary' : 'btn-secondary' ]"
            title="Segmentation (Ctrl+3)"
            @click="onPushPanelBtn"
        >
            <i class="click-through fas fa-align-left" />
        </button>
        <button
            id="trans-panel-btn"
            type="button"
            data-target="visualisation"
            class="open-panel nav-item btn"
            :class="[ visible_panels.visualisation ? 'btn-primary' : 'btn-secondary' ]"
            title="Transcription (Ctrl+4)"
            @click="onPushPanelBtn"
        >
            <i class="click-through fas fa-language" />
        </button>
        <button
            id="diplo-panel-btn"
            type="button"
            data-target="diplomatic"
            class="open-panel nav-item btn"
            :class="[ visible_panels.diplomatic ? 'btn-primary' : 'btn-secondary' ]"
            title="Text (Ctrl+5)"

            @click="onPushPanelBtn"
        >
            <i class="click-through fas fa-list-ol" />
        </button>
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
        window.addEventListener("keyup", function(ev) {
            let panels = [...document.getElementById("toggle-panels").querySelectorAll("button")].map((e)=>e.dataset.target);

            if (ev.ctrlKey && ev.keyCode >=49 && ev.keyCode <=48+panels.length) {
                this.togglePanel(panels[ev.keyCode-49]);
            }
        }.bind(this));
    },
    methods: {
        togglePanel(target) {
            this.$store.dispatch("document/togglePanel", target);
        },
        onPushPanelBtn(evt) {
            this.togglePanel(evt.target.getAttribute("data-target"));
        }
    }
}
</script>

<style scoped>
</style>
