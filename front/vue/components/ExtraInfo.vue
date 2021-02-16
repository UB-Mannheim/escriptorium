<template>
    <div>
        <div class="nav-div nav-item ml-2">
            <span v-if="$store.state.document.name" id="part-name">{{ $store.state.document.name }}</span>
            <span id="part-title" v-if="$store.state.parts.loaded">{{ $store.state.parts.title }} - {{ $store.state.parts.filename }} - ({{ imageSize }})</span>
            <span class="loading" v-if="!$store.state.parts.loaded">Loading&#8230;</span>
        </div>
    </div>
</template>

<script>
export default {
    computed: {
        imageSize() {
            return this.$store.state.parts.image.size[0]+'x'+this.$store.state.parts.image.size[1];
        },
    }
}
</script>

<style scoped>
</style>
