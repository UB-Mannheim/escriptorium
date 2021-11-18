<template>
    <div>
        <div class="nav-div nav-item ml-2">
            <span v-if="$store.state.document.name" id="part-name">{{ $store.state.document.name }}</span>
            <span id="part-title"
                  v-if="$store.state.parts.loaded"
                  title="Click to go to another Element (Ctrl+Home)."
                  data-toggle="modal"
                  data-target="#gotoModal"
                  role="button">{{ $store.state.parts.title }} - {{ $store.state.parts.filename }} - ({{ imageSize }}) - {{ $store.state.parts.image_file_size | prettyBytes }}</span>
            <span class="loading" v-if="!$store.state.parts.loaded">Loading&#8230;</span>
        </div>

        <div id="gotoModal"
             class="modal ui-draggable show"
             tabindex="-1"
             role="dialog">
          <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
              <div class="modal-body">
                Element #
                <input type="number"
                       v-if="$store.state.parts.loaded"
                       min="1"
                       :max="$store.state.document.partsCount"
                       width="100%"
                       v-bind:value="$store.state.parts.order+1"
                       @change.lazy="goTo"/>
                / {{$store.state.document.partsCount}}
              </div>
            </div>
          </div>
        </div>
    </div>
</template>

<script>
export default {
    async created() {
        document.addEventListener('keyup', async function(event) {
            if (event.ctrlKey && event.keyCode == 36) { // Home
                $('#gotoModal').modal('show');
            }
        });
    },
    computed: {
        imageSize() {
            return this.$store.state.parts.image.size[0]+'x'+this.$store.state.parts.image.size[1];
        },
    },
    methods: {
        async goTo(ev) {
            if (ev.target.value > 0 && ev.target.value <= parseInt(ev.target.attributes.max.value)) {
              await this.$store.dispatch('parts/loadPartByOrder', ev.target.value-1);
              $('#gotoModal').modal('hide');
            }
        }
    }
}
</script>

<style scoped>
</style>
