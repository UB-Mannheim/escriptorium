<template>
    <form
        method="get"
        action="/search/"
    >
        <input
            v-if="data?.projectId"
            name="project"
            type="text"
            :value="data?.projectId"
            hidden
        >
        <input
            v-if="data?.documentId"
            name="document"
            type="text"
            :value="data?.documentId"
            hidden
        >
        <div
            class="escr-search-form"
        >
            <h3>Search Text in {{ data?.searchScope }}</h3>
            <TextField
                :disabled="data?.disabled"
                name="query"
                help-text="Surround one or more terms with quotation marks to deactivate fuzziness."
                placeholder="Text to search"
            />
        </div>
        <EscrButton
            :disabled="data?.disabled"
            :on-click="data?.onSearch || (() => {})"
            label="Search"
            color="primary"
            type="submit"
        />
    </form>
</template>
<script>
import EscrButton from "../Button/Button.vue";
import TextField from "../TextField/TextField.vue";
import "./SearchPanel.css";

export default {
    name: "EscrSharePanel",
    components: { EscrButton, TextField },
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
