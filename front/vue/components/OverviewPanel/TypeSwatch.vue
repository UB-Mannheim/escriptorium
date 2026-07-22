<template>
    <span class="escr-type-swatch">
        <span
            v-if="gradient"
            class="escr-type-swatch-color escr-type-swatch-gradient"
        />
        <span
            v-else-if="color"
            class="escr-type-swatch-color"
            :style="{ backgroundColor: color }"
        />
        {{ name }}
    </span>
</template>

<script>
export default {
    name: "TypeSwatch",
    props: {
        color: {
            type: String,
            default: null,
        },
        // true when the element has no region (shown as a gray gradient instead of a color)
        gradient: {
            type: Boolean,
            default: false,
        },
        name: {
            type: String,
            required: true,
        },
    },
};
</script>

<style scoped>
.escr-type-swatch {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
}

.escr-type-swatch-color {
    display: inline-block;
    width: 0.7rem;
    height: 0.7rem;
    flex: 0 0 auto;
    border-radius: 2px;
}

.escr-type-swatch-gradient {
    background: linear-gradient(135deg, #bbb, #666);
}
</style>
