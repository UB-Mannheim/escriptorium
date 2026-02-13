<template>
    <div
        class="escr-multiselect-dropdown"
        :style="{ marginBottom: dropdownSpacing }"
    >
        <div class="escr-multiselect-actions">
            <button
                type="button"
                class="escr-multiselect-action-btn"
                @click.stop="selectAll"
                :disabled="disabled"
            >
                Select All
            </button>
            <button
                type="button"
                class="escr-multiselect-action-btn"
                @click.stop="clearAll"
                :disabled="disabled"
            >
                Clear
            </button>
        </div>
        <div
            ref="trigger"
            class="escr-multiselect-trigger"
            :class="{ 'escr-multiselect-trigger--disabled': disabled, 'escr-multiselect-trigger--open': showDropdown }"
            :disabled="disabled"
            @click="toggleDropdown"
            @keydown.enter.prevent="toggleDropdown"
            @keydown.space.prevent="toggleDropdown"
            @keydown.escape="closeDropdown"
            tabindex="0"
            role="button"
            :aria-label="label"
            :aria-expanded="showDropdown"
        >
            <span class="escr-multiselect-trigger-text">
                {{ triggerText }}
            </span>
            <ChevronDownIcon />
        </div>
        <div
            v-if="showDropdown"
            class="escr-multiselect-options"
            @mousedown.prevent
        >
            <div class="escr-multiselect-search">
                <input
                    ref="searchInput"
                    type="text"
                    v-model="searchText"
                    placeholder="Search..."
                    class="escr-multiselect-search-input"
                    @click.stop
                >
            </div>
            <div class="escr-multiselect-list">
                <div
                    v-if="filteredOptions.length === 0"
                    class="escr-multiselect-no-results"
                >
                    No results found
                </div>
                <label
                    v-for="option in filteredOptions"
                    :key="option.value"
                    class="escr-multiselect-option"
                    @click.stop
                >
                    <input
                        type="checkbox"
                        :value="option.value"
                        :checked="option.selected"
                        @change="handleOptionChange"
                    >
                    <span>{{ option.label }}</span>
                </label>
            </div>
        </div>
    </div>
</template>

<script>
import ChevronDownIcon from "../Icons/ChevronDownIcon/ChevronDownIcon.vue";
import "./MultiSelectDropdown.css";

export default {
    name: "EscrMultiSelectDropdown",
    components: { ChevronDownIcon },
    props: {
        /**
         * Boolean indicating if the dropdown should be disabled.
         */
        disabled: {
            type: Boolean,
            default: false,
        },
        /**
         * Label for accessibility.
         */
        label: {
            type: String,
            default: "",
        },
        /**
         * Placeholder text when nothing is selected
         */
        placeholder: {
            type: String,
            default: "Select items...",
        },
        /**
         * List of options:
         * [
         *   { value: String, label: String, selected: Boolean }
         * ]
         */
        options: {
            type: Array,
            required: true,
        },
        /**
         * Callback for changing selections.
         */
        onChange: {
            type: Function,
            required: true,
        },
    },
    data() {
        return {
            searchText: "",
            showDropdown: false,
        };
    },
    computed: {
        /**
         * Filter options based on search text
         */
        filteredOptions() {
            const search = this.searchText.toLowerCase();
            if (!search) {
                return this.options;
            }

            return this.options.filter(option =>
                option.label.toLowerCase().includes(search)
            );
        },
        /**
         * Count of selected options
         */
        selectedCount() {
            return this.options.filter(opt => opt.selected).length;
        },
        /**
         * Text to display on the trigger button
         */
        triggerText() {
            if (this.selectedCount === 0) {
                return this.placeholder;
            }
            return `${this.selectedCount} selected`;
        },
        /**
         * Calculate dynamic spacing for dropdown when open
         */
        dropdownSpacing() {
            if (!this.showDropdown) {
                return '0px';
            }

            // Search input: 40px, max list height: 200px
            const maxHeight = 40 + 200;
            return `${maxHeight + 10}px`;
        },
    },
    methods: {
        toggleDropdown() {
            if (this.disabled) return;
            this.showDropdown = !this.showDropdown;
            if (this.showDropdown) {
                this.$nextTick(() => {
                    if (this.$refs.searchInput) {
                        this.$refs.searchInput.focus();
                    }
                });
                document.addEventListener('click', this.handleClickOutside);
            } else {
                document.removeEventListener('click', this.handleClickOutside);
            }
        },
        closeDropdown() {
            this.showDropdown = false;
            document.removeEventListener('click', this.handleClickOutside);
        },
        handleClickOutside(e) {
            if (this.$el && !this.$el.contains(e.target)) {
                this.closeDropdown();
            }
        },
        handleOptionChange(e) {
            this.onChange(e);
        },
        selectAll() {
            // Select all visible (filtered) options
            this.filteredOptions.forEach(option => {
                if (!option.selected) {
                    this.onChange({
                        target: {
                            value: option.value,
                            checked: true,
                        },
                    });
                }
            });
        },
        clearAll() {
            // Clear all selected options
            this.options.forEach(option => {
                if (option.selected) {
                    this.onChange({
                        target: {
                            value: option.value,
                            checked: false,
                        },
                    });
                }
            });
        },
    },
    beforeUnmount() {
        document.removeEventListener('click', this.handleClickOutside);
    },
};
</script>
