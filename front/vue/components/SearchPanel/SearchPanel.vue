<template>
    <form
        method="get"
        action="/search/"
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
            <h3>Search Text in {{ data && data.searchScope }}</h3>
            <label class="escr-text-field escr-form-field">
                <input
                    type="text"
                    placeholder="Text to search"
                    aria-label="Search"
                    :disabled="data && data.disabled"
                    name="query"
                >
                <span
                    class="escr-help-text"
                >
                    Surround one or more terms with quotation marks to deactivate fuzziness.
                </span>
            </label>
        </div>
        <EscrButton
            :disabled="data && data.disabled"
            :on-click="(data && data.onSearch) || (() => {})"
            label="Search"
            color="primary"
            type="submit"
        />
    </form>
</template>
<script>
import EscrButton from "../Button/Button.vue";
import "./SearchPanel.css";

export default {
    name: "EscrSearchPanel",
    components: { EscrButton },
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
}
</script>
