import Vue from "vue";
import EscrAutocompleteDropdown from "../components/AutocompleteDropdown/AutocompleteDropdown.vue";

document.querySelectorAll(".js-autocomplete").forEach((field) => {
    const isSelect = field.tagName === "SELECT";
    const choices = Array.from((isSelect ? field.options : field.list?.options) || []);
    const options = choices.filter((choice) => choice.value).map((choice) => ({
        value: choice.value,
        label: isSelect ? choice.text : choice.value,
        hint: isSelect ? "" : choice.text.trim(),
    }));
    const mount = document.createElement("div");
    field.before(mount);
    field.hidden = true;
    field.required = false;
    if (!options.some((option) => option.value === field.value)) field.value = "";

    new Vue({
        el: mount,
        data: { value: field.value },
        computed: {
            optionGroups() {
                if (!options.length) return [];
                return [{
                    options: options.map((option) => ({
                        ...option,
                        selected: option.value === this.value,
                    })),
                }];
            },
        },
        render(h) {
            return h(EscrAutocompleteDropdown, {
                props: {
                    label: field.title,
                    placeholder: isSelect ? choices[0]?.text : field.placeholder,
                    allowCustomValue: !isSelect,
                    matchesOnly: !isSelect,
                    optionGroups: this.optionGroups,
                    onChange: (e) => {
                        this.value = e.target.value;
                        field.value = e.target.value;
                    },
                },
            });
        },
    });
});
