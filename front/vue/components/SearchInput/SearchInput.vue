<template>
    <div class="escr-search-input">
        <input
            type="text"
            :value="value"
            :placeholder="placeholder"
            :disabled="disabled"
            @input="handleInput"
            @keyup.enter="onEnter"
            class="escr-search-input-field"
        />
        <button
            v-if="value"
            @click="handleClear"
            :disabled="disabled"
            class="escr-search-input-clear"
            aria-label="Clear search"
        >
            ×
        </button>
    </div>
</template>

<script>
export default {
    name: "EscrSearchInput",
    props: {
        /**
         * The current value of the search input.
         */
        value: {
            type: String,
            default: "",
        },
        /**
         * Placeholder text for the input.
         */
        placeholder: {
            type: String,
            default: "Search...",
        },
        /**
         * Whether the input is disabled.
         */
        disabled: {
            type: Boolean,
            default: false,
        },
        /**
         * Callback when the input value changes.
         */
        onInput: {
            type: Function,
            default: () => {},
        },
        /**
         * Callback when clear button is clicked.
         */
        onClear: {
            type: Function,
            default: () => {},
        },
        /**
         * Callback when Enter key is pressed.
         */
        onEnter: {
            type: Function,
            default: () => {},
        },
    },
    methods: {
        handleInput(event) {
            this.onInput(event.target.value);
        },
        handleClear() {
            this.onClear();
        },
    },
};
</script>

<style scoped>
.escr-search-input {
    position: relative;
    display: inline-flex;
    align-items: center;
}

.escr-search-input-field {
    padding: 0.5rem 2rem 0.5rem 0.75rem;
    border: 1px solid var(--text3);
    border-radius: 0.25rem;
    font-size: 0.875rem;
    line-height: 1.25rem;
    width: 200px;
    background-color: var(--background1);
    color: var(--text1);
    transition: border-color 0.15s ease-in-out, box-shadow 0.15s ease-in-out;
}

.escr-search-input-field:focus {
    outline: none;
    border-color: var(--primary);
    box-shadow: 0 0 0 3px var(--primary-focus);
}

.escr-search-input-field:disabled {
    background-color: var(--background2);
    cursor: not-allowed;
    opacity: 0.6;
}

.escr-search-input-clear {
    position: absolute;
    right: 0.5rem;
    background: none;
    border: none;
    font-size: 1.25rem;
    line-height: 1;
    color: var(--text2);
    cursor: pointer;
    padding: 0;
    width: 1.25rem;
    height: 1.25rem;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: color 0.15s ease-in-out;
}

.escr-search-input-clear:hover:not(:disabled) {
    color: var(--text1);
}

.escr-search-input-clear:disabled {
    cursor: not-allowed;
    opacity: 0.6;
}
</style>
