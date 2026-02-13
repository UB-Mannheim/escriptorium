<template>
    <div 
        class="escr-autocomplete-dropdown"
        :style="{ marginBottom: dropdownSpacing }"
    >
        <input
            ref="input"
            type="text"
            :value="searchText"
            :placeholder="placeholder"
            :disabled="disabled"
            :aria-label="label"
            @input="handleInput"
            @focus="handleFocus"
            @blur="handleBlur"
            @keydown="handleKeyDown"
            autocomplete="off"
        >
        <ChevronDownIcon />
        <div
            v-if="showDropdown"
            class="escr-autocomplete-options"
        >
            <div
                v-if="filteredOptions.length === 0"
                class="escr-autocomplete-no-results"
            >
                No results found
            </div>
            <template v-else>
                <div
                    v-for="(group, index) in filteredOptions"
                    :key="`group-${index}`"
                >
                    <div
                        v-if="group.label"
                        class="escr-autocomplete-group-label"
                    >
                        {{ group.label }}
                    </div>
                    <div
                        v-for="(option, optIndex) in group.options"
                        :key="`option-${index}-${optIndex}`"
                        class="escr-autocomplete-option"
                        :class="{ 'escr-autocomplete-option--selected': option.selected }"
                        @mousedown.prevent="selectOption(option)"
                    >
                        {{ option.label }}
                    </div>
                </div>
            </template>
        </div>
    </div>
</template>

<script>
import ChevronDownIcon from "../Icons/ChevronDownIcon/ChevronDownIcon.vue";
import "./AutocompleteDropdown.css";

export default {
    name: "EscrAutocompleteDropdown",
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
         * Optional label, only used as an aria-label for accessibility.
         */
        label: {
            type: String,
            default: "",
        },
        /**
         * Placeholder text for the input
         */
        placeholder: {
            type: String,
            default: "Select or search...",
        },
        /**
         * List of option groups, each containing a label and options:
         * [
         *   {
         *     label: "Group Name",
         *     options: [
         *       { value: String, label: String, selected: Boolean }
         *     ]
         *   }
         * ]
         */
        optionGroups: {
            type: Array,
            required: true,
        },
        /**
         * Callback for changing the selected option.
         */
        onChange: {
            type: Function,
            required: true,
        },
        /**
         * Allow user to enter custom values not in the list.
         */
        allowCustomValue: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        return {
            searchText: "",
            showDropdown: false,
            blurTimeout: null,
        };
    },
    computed: {
        /**
         * Filter option groups based on search text
         */
        filteredOptions() {
            const search = this.searchText.toLowerCase();
            if (!search) {
                return this.optionGroups;
            }

            return this.optionGroups
                .map(group => ({
                    label: group.label,
                    options: group.options.filter(option =>
                        option.label.toLowerCase().includes(search)
                    ),
                }))
                .filter(group => group.options.length > 0);
        },
        /**
         * Get the currently selected option across all groups
         */
        selectedOption() {
            for (const group of this.optionGroups) {
                const selected = group.options.find(opt => opt.selected);
                if (selected) return selected;
            }
            return null;
        },
        /**
         * calculate dynamic spacing for dropdown when open
         */
        dropdownSpacing() {
            if (!this.showDropdown) {
                return '0px';
            }

            let height = 0;
            
            if (this.filteredOptions.length === 0) {
                height = 48;
            } else {
                this.filteredOptions.forEach(group => {
                    if (group.label) {
                        height += 32;
                    }
                    height += group.options.length * 30;
                });
            }
            const finalHeight = Math.min(height, 300);
            return `${finalHeight + 10}px`;
        },
    },
    watch: {
        selectedOption: {
            immediate: true,
            handler(option) {
                this.searchText = option ? option.label : "";
            },
        },
    },
    methods: {
        handleInput(e) {
            this.searchText = e.target.value;
            this.showDropdown = true;
            // If custom values are allowed, trigger onChange on input
            if (this.allowCustomValue) {
                this.onChange({ target: { value: e.target.value } });
            }
        },
        handleFocus() {
            if (this.blurTimeout) {
                clearTimeout(this.blurTimeout);
                this.blurTimeout = null;
            }
            this.showDropdown = true;
        },
        handleBlur() {
            // Delay to allow click on option
            this.blurTimeout = setTimeout(() => {
                this.showDropdown = false;
                // If custom values are allowed, ensure final value is sent
                if (this.allowCustomValue && this.searchText) {
                    this.onChange({ target: { value: this.searchText } });
                }
                this.blurTimeout = null;
            }, 200);
        },
        handleKeyDown(e) {
            if (e.key === "Escape") {
                this.showDropdown = false;
                this.$refs.input.blur();
            }
        },
        selectOption(option) {
            if (this.blurTimeout) {
                clearTimeout(this.blurTimeout);
                this.blurTimeout = null;
            }
            this.searchText = option.label;
            this.showDropdown = false;
            this.onChange({ target: { value: option.value } });
        },
    },
};
</script>
