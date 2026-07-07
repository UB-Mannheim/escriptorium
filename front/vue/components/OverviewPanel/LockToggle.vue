<template>
    <button
        type="button"
        class="escr-lock-toggle"
        :title="locked ? 'Unlock region' : 'Lock region'"
        :aria-label="locked ? 'Unlock region' : 'Lock region'"
        :aria-pressed="locked"
        @click.stop="onClick"
    >
        <LockIcon v-if="locked" />
        <LockOpenIcon v-else />
    </button>
</template>

<script>
import LockIcon from "../Icons/LockIcon/LockIcon.vue";
import LockOpenIcon from "../Icons/LockOpenIcon/LockOpenIcon.vue";

export default {
    name: "LockToggle",
    components: { LockIcon, LockOpenIcon },
    props: {
        locked: {
            type: Boolean,
            default: false,
        },
        pk: {
            type: Number,
            required: true,
        },
    },
    methods: {
        onClick() {
            this.$store.dispatch("regions/toggleLocked", this.pk);
        },
    },
};
</script>

<style scoped>
.escr-lock-toggle {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: none;
    border: none;
    padding: 0.2rem;
    cursor: pointer;
    color: inherit;
}

.escr-lock-toggle:hover {
    color: var(--secondary);
}
</style>
