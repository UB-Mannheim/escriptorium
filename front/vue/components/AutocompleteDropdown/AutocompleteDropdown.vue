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
        <button
            v-if="searchText && !disabled"
            class="escr-autocomplete-clear"
            type="button"
            :aria-label="`Clear ${label}`"
            @mousedown.prevent="clearValue"
        >×</button>
        <ChevronDownIcon v-else />
        <div
            v-if="showDropdown"
            class="escr-autocomplete-options"
        >
            <div
                v-if="filteredOptions.length === 0 && searchText && allowCustomValue"
                class="escr-autocomplete-new-option"
            >
                <span class="escr-new-option-icon">➕</span>
                <span>Create new layer: <strong>{{ searchText }}</strong></span>
            </div>
            <div
                v-else-if="filteredOptions.length === 0"
                class="escr-autocomplete-no-results"
            >
                No results found
            </div>
            <template v-else>
                <div
                    v-if="allowCustomValue && searchText && !hasExactMatch"
                    class="escr-autocomplete-new-option escr-autocomplete-new-option--clickable"
                    :class="{ 'escr-autocomplete-new-option--highlighted': highlightedIndex === -1 }"
                    @mousedown.prevent="selectCustomValue"
                    @mouseenter="highlightedIndex = -1"
                >
                    <span class="escr-new-option-icon">➕</span>
                    <span>Create new layer: <strong>{{ searchText }}</strong></span>
                </div>
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
                        :class="{
                            'escr-autocomplete-option--selected': option.selected,
                            'escr-autocomplete-option--highlighted': getFlatIndex(index, optIndex) === highlightedIndex
                        }"
                        @mousedown.prevent="selectOption(option)"
                        @mouseenter="highlightedIndex = getFlatIndex(index, optIndex)"
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
            highlightedIndex: 0,
            isClearing: false,
            isUserTyping: false,
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
         * Check if search text exactly matches any option
         */
        hasExactMatch() {
            const search = this.searchText.toLowerCase();
            return this.optionGroups.some(group =>
                group.options.some(option => option.label.toLowerCase() === search)
            );
        },
        /**
         * Flatten all options from groups into a single array for keyboard navigation
         */
        flattenedOptions() {
            const flattened = [];
            this.filteredOptions.forEach(group => {
                group.options.forEach(option => {
                    flattened.push(option);
                });
            });
            return flattened;
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
                if (this.allowCustomValue && this.searchText && !this.hasExactMatch) {
                    height += 38;
                }
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
                if (this.isClearing) {
                    this.isClearing = false;
                    return;
                }
                if (this.isUserTyping) {
                    this.isUserTyping = false;
                    return;
                }
                this.searchText = option ? option.label : "";
            },
        },
        filteredOptions() {
            // Reset highlighted index when filtered options change
            this.highlightedIndex = 0;
        },
    },
    methods: {
        handleInput(e) {
            this.isUserTyping = true;
            this.searchText = e.target.value;
            this.showDropdown = true;
            this.highlightedIndex = 0;

            // If custom values are allowed, trigger onChange on input
            if (this.allowCustomValue) {
                this.onChange({ target: { value: e.target.value } });
            }
            // If field is cleared (empty), always trigger onChange to clear selection
            else if (e.target.value === "") {
                this.onChange({ target: { value: "" } });
            }
        },
        handleFocus() {
            if (this.blurTimeout) {
                clearTimeout(this.blurTimeout);
                this.blurTimeout = null;
            }
            this.showDropdown = true;
            this.highlightedIndex = 0;
        },
        handleBlur() {
            // Delay to allow click on option
            this.blurTimeout = setTimeout(() => {
                this.showDropdown = false;

                // If custom values are allowed, ensure final value is sent
                if (this.allowCustomValue && this.searchText) {
                    this.onChange({ target: { value: this.searchText } });
                }
                // If custom values NOT allowed and text doesn't match, revert to selected value
                else if (!this.allowCustomValue) {
                    // If there's no exact match and searchText is not empty, restore the selected option
                    if (this.searchText && !this.hasExactMatch) {
                        this.searchText = this.selectedOption ? this.selectedOption.label : "";
                    }
                }

                this.blurTimeout = null;
            }, 200);
        },
        handleKeyDown(e) {
            if (e.key === "Escape") {
                this.showDropdown = false;
                this.$refs.input.blur();
            } else if (e.key === "ArrowDown") {
                e.preventDefault();
                if (!this.showDropdown) {
                    this.showDropdown = true;
                    this.highlightedIndex = 0;
                } else {
                    const hasCustomOption = this.allowCustomValue && this.searchText && !this.hasExactMatch;
                    const maxIndex = this.flattenedOptions.length - 1;

                    if (hasCustomOption && this.highlightedIndex === -1) {
                        this.highlightedIndex = 0;
                    } else if (this.highlightedIndex < maxIndex) {
                        this.highlightedIndex++;
                    } else if (hasCustomOption) {
                        this.highlightedIndex = -1; // Loop back to custom option
                    } else {
                        this.highlightedIndex = 0; // Loop back to first
                    }
                }
            } else if (e.key === "ArrowUp") {
                e.preventDefault();
                if (!this.showDropdown) {
                    this.showDropdown = true;
                    this.highlightedIndex = 0;
                } else {
                    const hasCustomOption = this.allowCustomValue && this.searchText && !this.hasExactMatch;
                    const maxIndex = this.flattenedOptions.length - 1;

                    if (this.highlightedIndex === 0 && hasCustomOption) {
                        this.highlightedIndex = -1; // Go to custom option
                    } else if (this.highlightedIndex > 0) {
                        this.highlightedIndex--;
                    } else if (this.highlightedIndex === -1) {
                        this.highlightedIndex = maxIndex; // Go to last option
                    } else {
                        this.highlightedIndex = maxIndex; // Loop to last
                    }
                }
            } else if (e.key === "Enter") {
                e.preventDefault(); // Prevent form submission

                if (!this.showDropdown) {
                    return;
                }

                // Priority 1: If typing a custom value that doesn't exactly match, use it
                if (this.allowCustomValue && this.searchText && !this.hasExactMatch) {
                    this.selectCustomValue();
                }
                // Priority 2: If custom option is highlighted (index -1)
                else if (this.highlightedIndex === -1 && this.allowCustomValue && this.searchText) {
                    this.selectCustomValue();
                }
                // Priority 3: Select the highlighted option from filtered list
                else if (this.flattenedOptions.length > 0 && this.highlightedIndex >= 0) {
                    const option = this.flattenedOptions[this.highlightedIndex];
                    if (option) {
                        this.selectOption(option);
                    }
                }
                // Priority 4: Fallback to custom value
                else if (this.allowCustomValue && this.searchText) {
                    this.selectCustomValue();
                }
                // Priority 5: Just close
                else {
                    this.showDropdown = false;
                    this.$refs.input.blur();
                }
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
            this.$refs.input.blur();
        },
        selectCustomValue() {
            if (this.blurTimeout) {
                clearTimeout(this.blurTimeout);
                this.blurTimeout = null;
            }
            this.showDropdown = false;
            this.onChange({ target: { value: this.searchText } });
            this.$refs.input.blur();
        },
        clearValue() {
            if (this.blurTimeout) {
                clearTimeout(this.blurTimeout);
                this.blurTimeout = null;
            }
            this.isClearing = true;
            this.searchText = "";
            this.showDropdown = false;
            this.onChange({ target: { value: "" } });
            this.$refs.input.blur();
        },
        /**
         * Get the flat index for an option given its group and option index
         */
        getFlatIndex(groupIndex, optionIndex) {
            let flatIndex = 0;
            for (let i = 0; i < groupIndex; i++) {
                flatIndex += this.filteredOptions[i].options.length;
            }
            flatIndex += optionIndex;
            return flatIndex;
        },
    },
};
</script>
