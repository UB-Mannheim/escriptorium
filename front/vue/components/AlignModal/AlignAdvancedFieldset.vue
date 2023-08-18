<template>
    <fieldset class="escr-align-advanced">
        <legend><h3>Advanced Settings</h3></legend>
        <label class="escr-text-field">
            <div>
                <span>Line length threshold</span>
                <VDropdown
                    theme="escr-tooltip"
                    @apply-show="showTooltip({ form: 'align', tooltip: 'threshold' })"
                    @apply-hide="hideTooltip({ form: 'align', tooltip: 'threshold' })"
                >
                    <EscrButton
                        color="link-secondary"
                        size="small"
                        :disabled="disabled"
                        :on-click="() => {}"
                    >
                        <template #button-icon>
                            <InfoFilledIcon v-if="tooltipShown && tooltipShown.threshold" />
                            <InfoOutlineIcon v-else />
                        </template>
                    </EscrButton>
                    <template #popper>
                        <span>
                            Minimum proportion (0.0-1.0) of aligned line length to original
                            transcription, below which matches are ignored. At 0.0, all matches
                            are accepted.
                        </span>
                    </template>
                </VDropdown>
            </div>
            <input
                type="number"
                step="0.1"
                min="0.0"
                max="1.0"
                placeholder="Threshold"
                :disabled="disabled"
                :value="threshold"
                @change="(e) => handleChange('threshold', e.target.value)"
            >
        </label>
        <label class="escr-text-field">
            <div>
                <span>N-gram</span>
                <VDropdown
                    theme="escr-tooltip"
                    @apply-show="showTooltip({ form: 'align', tooltip: 'ngram' })"
                    @apply-hide="hideTooltip({ form: 'align', tooltip: 'ngram' })"
                >
                    <EscrButton
                        color="link-secondary"
                        size="small"
                        :disabled="disabled"
                        :on-click="() => {}"
                    >
                        <template #button-icon>
                            <InfoFilledIcon v-if="tooltipShown && tooltipShown.ngram" />
                            <InfoOutlineIcon v-else />
                        </template>
                    </EscrButton>
                    <template #popper>
                        <span>
                            Length (2–25) of token sequences to compare; 25 should work well for
                            at least moderately clean OCR. For very poor OCR, lower to 3 or 4.
                        </span>
                    </template>
                </VDropdown>
            </div>
            <input
                type="number"
                min="2"
                max="25"
                placeholder="N-gram"
                :disabled="disabled"
                :value="ngram"
                @change="(e) => handleChange('ngram', e.target.value)"
            >
        </label>
        <label class="escr-text-field">
            <div>
                <span>Beam size</span>
                <VDropdown
                    theme="escr-tooltip"
                    @apply-show="showTooltip({ form: 'align', tooltip: 'beamSize' })"
                    @apply-hide="hideTooltip({ form: 'align', tooltip: 'beamSize' })"
                >
                    <EscrButton
                        color="link-secondary"
                        size="small"
                        :disabled="disabled"
                        :on-click="() => {}"
                    >
                        <template #button-icon>
                            <InfoFilledIcon v-if="tooltipShown && tooltipShown.beamSize" />
                            <InfoOutlineIcon v-else />
                        </template>
                    </EscrButton>
                    <template #popper>
                        <span>
                            1-100, enables beam search; if this and max offset are left unset, beam
                            search will be on and beam size set to 20. Higher beam size
                            will result in slower computation but more accurate results.
                        </span>
                    </template>
                </VDropdown>
            </div>
            <input
                type="number"
                min="0"
                max="100"
                placeholder="Beam size"
                :disabled="disabled || maxOffset !== ''"
                :value="beamSize"
                @change="(e) => handleChange('beamSize', e.target.value)"
            >
        </label>
        <label class="escr-text-field">
            <div>
                <span>Max offset</span>
                <VDropdown
                    theme="escr-tooltip"
                    @apply-show="showTooltip({ form: 'align', tooltip: 'maxOffset' })"
                    @apply-hide="hideTooltip({ form: 'align', tooltip: 'maxOffset' })"
                >
                    <EscrButton
                        color="link-secondary"
                        size="small"
                        :disabled="disabled"
                        :on-click="() => {}"
                    >
                        <template #button-icon>
                            <InfoFilledIcon v-if="tooltipShown && tooltipShown.maxOffset" />
                            <InfoOutlineIcon v-else />
                        </template>
                    </EscrButton>
                    <template #popper>
                        <span>
                            Enables max-offset and disables beam search. Maximum number of
                            characters (20–80) difference between the aligned witness text
                            and the original transcription.
                        </span>
                    </template>
                </VDropdown>
            </div>
            <input
                type="number"
                min="0"
                max="80"
                placeholder="Max offset"
                :disabled="disabled || beamSize !== ''"
                :value="maxOffset"
                @change="(e) => handleChange('maxOffset', e.target.value)"
            >
        </label>
        <label class="escr-text-field">
            <div>
                <span>Gap</span>
                <VDropdown
                    theme="escr-tooltip"
                    @apply-show="showTooltip({ form: 'align', tooltip: 'gap' })"
                    @apply-hide="hideTooltip({ form: 'align', tooltip: 'gap' })"
                >
                    <EscrButton
                        color="link-secondary"
                        size="small"
                        :disabled="disabled"
                        :on-click="() => {}"
                    >
                        <template #button-icon>
                            <InfoFilledIcon v-if="tooltipShown && tooltipShown.gap" />
                            <InfoOutlineIcon v-else />
                        </template>
                    </EscrButton>
                    <template #popper>
                        <span>
                            The distance between matching unique n-grams; 600 should work well for
                            clean OCR or texts where passages align to different portions of the
                            witness text. To force end-to-end alignment of two documents, increase
                            to 1,000,000.
                        </span>
                    </template>
                </VDropdown>
            </div>
            <input
                type="number"
                min="1"
                max="1000000"
                placeholder="Gap"
                :disabled="disabled"
                :value="gap"
                @change="(e) => handleChange('gap', e.target.value)"
            >
        </label>
    </fieldset>
</template>
<script>
import { mapActions, mapState } from "vuex";
import EscrButton from "../Button/Button.vue";
import InfoFilledIcon from "../Icons/InfoFilledIcon/InfoFilledIcon.vue";
import InfoOutlineIcon from "../Icons/InfoOutlineIcon/InfoOutlineIcon.vue";
import { Dropdown as VDropdown } from "floating-vue";

export default {
    name: "EscrAlignAdvancedFieldset",
    components: { EscrButton, InfoFilledIcon, InfoOutlineIcon, VDropdown },
    props: {
        /**
         * Boolean indicating whether or not the form fields should be disabled.
         */
        disabled: {
            type: Boolean,
            required: true,
        },
    },
    computed: {
        ...mapState({
            threshold: (state) => state.forms.align.threshold,
            ngram: (state) => state.forms.align.ngram,
            beamSize: (state) => state.forms.align.beamSize,
            maxOffset: (state) => state.forms.align.maxOffset,
            gap: (state) => state.forms.align.gap,
            tooltipShown: (state) => state.forms.align.tooltipShown,
        }),
    },
    mounted() {
        // scroll into view on mount
        this.$el.scrollIntoView({ behavior: "smooth" });
    },
    methods: {
        ...mapActions("forms", [
            "handleGenericInput",
            "hideTooltip",
            "showTooltip",
        ]),
        handleChange(field, value) {
            this.handleGenericInput({ form: "align", field, value });
        },
    },
}
</script>
