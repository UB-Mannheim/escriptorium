<template>
    <div id="escr-editor">
        <nav v-if="legacyModeEnabled">
            <div
                id="nav-tab"
                class="nav nav-tabs mb-3"
                role="tablist"
            >
                <slot />
                <ExtraInfo />
                <TranscriptionManagement />
                <ExtraNav />
            </div>
        </nav>
        <EditorNavigation
            v-else
            :disabled="!partsLoaded"
        />

        <TabContent :legacy-mode-enabled="legacyModeEnabled" />

        <ElementDetailsModal
            v-if="!legacyModeEnabled && modalOpen && modalOpen.elementDetails"
            :disabled="!partsLoaded"
            :on-cancel="closeElementDetailsModal"
            :on-save="onSavePart"
        />
    </div>
</template>

<script>
import { mapActions, mapState } from "vuex";
import EditorNavigation from "./EditorNavigation/EditorNavigation.vue";
import ElementDetailsModal from "./ElementDetailsModal/ElementDetailsModal.vue";
import ExtraInfo from "./ExtraInfo.vue";
import ExtraNav from "./ExtraNav.vue";
import TabContent from "./TabContent.vue";
import TranscriptionManagement from "./TranscriptionManagement.vue";
import "./Editor.css";

export default {
    name: "EscrEditor",
    components: {
        ElementDetailsModal,
        EditorNavigation,
        ExtraInfo,
        ExtraNav,
        TabContent,
        TranscriptionManagement,
    },
    props: {
        documentId: {
            type: String,
            required: true,
        },
        documentName: {
            type: String,
            required: true,
        },
        partId: {
            type: String,
            required: true,
        },
        defaultTextDirection: {
            type: String,
            required: true,
        },
        mainTextDirection: {
            type: String,
            required: true,
        },
        readDirection: {
            type: String,
            required: true,
        },
        /**
         * Whether or not legacy mode is enabled on this instance.
         */
        legacyModeEnabled: {
            type: Boolean,
            required: true,
        },
    },
    computed: {
        ...mapState({
            modalOpen: (state) => state.globalTools.modalOpen,
            partsLoaded: (state) => state.parts.loaded,
        }),
    },
    watch: {
        "$store.state.parts.pk": function(n, o) {
            if (n) {
                // set the new url
                window.history.pushState(
                    {}, "",
                    document.location.href.replace(/(part\/)\d+(\/edit)/,
                        "$1"+this.$store.state.parts.pk+"$2"));

                // set the 'image' tab btn to select the corresponding image
                var tabUrl = new URL($("#nav-img-tab").attr("href"),
                    window.location.origin);
                tabUrl.searchParams.set("select", this.$store.state.parts.pk);
                $("#nav-img-tab").attr("href", tabUrl);
            }
        },
        "$store.state.transcriptions.selectedTranscription": function(n, o) {
            let itrans = userProfile.get("initialTranscriptions") || {};
            itrans[this.documentId] = n;
            userProfile.set("initialTranscriptions", itrans);
            this.$store.dispatch("transcriptions/getCurrentContent", n);
        },
        "$store.state.transcriptions.comparedTranscriptions": function(n, o) {
            n.forEach(async function(tr, i) {
                if (!o.find((e)=>e==tr)) {
                    await this.$store.dispatch("transcriptions/fetchContent", tr);
                }
            }.bind(this));
        },
    },

    async created() {
        this.$store.commit("document/setId", this.documentId);
        this.$store.commit("document/setName", this.documentName);
        this.$store.commit("document/setDefaultTextDirection", this.defaultTextDirection);
        this.$store.commit("document/setMainTextDirection", this.mainTextDirection);
        this.$store.commit("document/setReadDirection", this.readDirection);
        try {
            await this.$store.dispatch("parts/fetchPart", {pk: this.partId});
            let tr = userProfile.get("initialTranscriptions")
                  && userProfile.get("initialTranscriptions")[this.$store.state.document.id]
                  || this.$store.state.transcriptions.all[0].pk;
            this.$store.commit("transcriptions/setSelectedTranscription", tr);
        } catch (err) {
            console.log("couldn't fetch part data!", err);
        }

        document.addEventListener("keydown", async function(event) {
            if (this.$store.state.document.blockShortcuts) return;
            if (event.keyCode == 33 ||  // page up
                (event.keyCode == (this.readDirection == "rtl"?39:37) && event.ctrlKey)) {  // arrow left

                await this.$store.dispatch("parts/loadPart", "previous");
                event.preventDefault();
            } else if (event.keyCode == 34 ||   // page down
                       (event.keyCode == (this.readDirection == "rtl"?37:39) &&
                       event.ctrlKey)) {  // arrow right
                await this.$store.dispatch("parts/loadPart", "next");
                event.preventDefault();
            }
        }.bind(this));

        // catch background emitted events when masks are recalculated
        let $alertsContainer = $("#alerts-container");
        $alertsContainer.on("part:mask", function(ev, data) {
            data.lines.forEach(function(lineData) {
                let line = this.$store.state.lines.all.find((l)=>l.pk == lineData.pk);
                if (line) {  // might have been deleted in the meantime
                    this.$store.commit("lines/update", lineData)
                }
            }.bind(this));
        }.bind(this));
    },
    methods: {
        ...mapActions("globalTools", ["closeElementDetailsModal"]),
        ...mapActions("parts", ["savePartChanges"]),
        async onSavePart() {
            await this.savePartChanges();
            this.closeElementDetailsModal();
        },
    }
}
</script>

<style scoped>
</style>
