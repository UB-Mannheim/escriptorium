<template>
    <form
        method="get"
        :action="searchAction"
    >
        <input
            v-if="data && data.projectId"
            name="project"
            type="text"
            :value="data && data.projectId"
            hidden
        >
        <input
            v-if="data && data.documentId"
            name="document"
            type="text"
            :value="data && data.documentId"
            hidden
        >
        <div
            class="escr-search-form"
        >
            <h3>{{ heading }}</h3>
            <label class="escr-text-field escr-form-field">
                <input
                    type="text"
                    :placeholder="$gettext('Text to search')"
                    :aria-label="$gettext('Search')"
                    :disabled="data && data.disabled"
                    name="query"
                >
                <span
                    class="escr-help-text"
                    v-translate
                >Surround one or more terms with quotation marks to deactivate fuzziness.</span>
            </label>
        </div>
        <EscrButton
            :disabled="data && data.disabled"
            :on-click="(data && data.onSearch) || (() => {})"
            :label="$gettext('Search')"
            color="primary"
            type="submit"
        />
    </form>
</template>
<script>
import EscrButton from "../Button/Button.vue";
import { SCRIPT_NAME } from "../../../src/scriptname.js";
import "./SearchPanel.css";

export default {
    name: "EscrSearchPanel",
    components: { EscrButton },
    computed: {
        searchAction() {
            return SCRIPT_NAME + "/search/";
        },
    },
    props: {
        /**
         * Data for the search panel, an object containing searchScope, disabled, and optionally
         * projectId and documentId.
         */
        data: {
            type: Object,
            required: true,
        },
    },
    computed: {
        /**
         * Panel heading, with the scope (e.g. "Project" or "Document")
         * interpolated at runtime.
         */
        heading() {
            return this.$gettextInterpolate(
                this.$gettext("Search Text in %{scope}"),
                { scope: (this.data && this.data.searchScope) || "" },
            );
        },
    },
}
</script>
