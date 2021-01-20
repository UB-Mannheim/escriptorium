<template>
    <div>
        <nav>
            <div class="nav nav-tabs mb-3" id="nav-tab" role="tablist">
                <slot></slot>
                <extrainfo :object="object"
                           :document-name="documentName"
                           @delete-transcription="deleteTranscription">
                </extrainfo>
                <extranav :show="show"></extranav>
            </div>
        </nav>

        <tabcontent :default-text-direction="defautTextDirection"
                    :main-text-direction="mainTextDirection"
                    :read-direction="readDirection"
                    :block-shortcuts="blockShortcuts"
                    :opened-panels="openedPanels"
                    :show="show"
                    @get-previous="getPrevious"
                    @get-next="getNext">
        </tabcontent>
    </div>
</template>

<script>
import ExtraInfo from './ExtraInfo.vue';
import ExtraNav from './ExtraNav.vue';
import TabContent from './TabContent.vue';

export default {
    props: [
        'object',
        'documentId',
        'documentName',
        'partId',
        'defautTextDirection',
        'mainTextDirection',
        'readDirection',
    ],
    data: function() {
        return {
            show: {
                source: userProfile.get('source-panel'),
                segmentation: userProfile.get('segmentation-panel'),
                visualisation: userProfile.get('visualisation-panel'),
                diplomatic: userProfile.get('diplomatic-panel')
            },
            blockShortcuts: false,
            selectedTranscription: null,
            comparedTranscriptions: [],
        };
    },
    computed: {
        openedPanels() {
            return [this.show.source,
                    this.show.segmentation,
                    this.show.visualisation].filter(p=>p===true);
        },
        navEditActive() {
            return window.location.pathname === "/document/" + this.documentId + "/parts/edit/" || window.location.pathname === "/document/" + this.documentId + "/part/" + this.$store.state.parts.pk + "/edit/";
        },
        partPk() {
            return this.$store.state.parts.pk
        }
    },
    watch: {
        '$store.state.parts.pk': function(n, o) {
            if (n) {
                // set the new url
                window.history.pushState(
                    {}, "",
                    document.location.href.replace(/(part\/)\d+(\/edit)/,
                                                   '$1'+this.$store.state.parts.pk+'$2'));

                // set the 'image' tab btn to select the corresponding image
                var tabUrl = new URL($('#nav-img-tab').attr('href'),
                                     window.location.origin);
                tabUrl.searchParams.set('select', this.$store.state.parts.pk);
                $('#nav-img-tab').attr('href', tabUrl);
            }
        },
        selectedTranscription: function(n, o) {
            let itrans = userProfile.get('initialTranscriptions') || {};
            itrans[this.documentId] = n;
            userProfile.set('initialTranscriptions', itrans);
            this.getCurrentContent(n);
        },
        comparedTranscriptions: function(n, o) {
            n.forEach(async function(tr, i) {
                if (!o.find(e=>e==tr)) {
                    await this.$store.dispatch('transcriptions/fetchContent', tr);
                }
            }.bind(this));
        },

        blockShortcuts(n, o) {
            // make sure the segmenter doesnt trigger keyboard shortcuts either
            if (this.$refs.segPanel) this.$refs.segPanel.segmenter.disableShortcuts = n;
        }
    },

    components: {
        'extrainfo': ExtraInfo,
        'extranav': ExtraNav,
        'tabcontent': TabContent,
    },

    async created() {
        this.$store.commit('parts/setDocumentId', this.documentId);
        try {
            await this.$store.dispatch('parts/fetchPart', this.partId);
            let tr = userProfile.get('initialTranscriptions')
                  && userProfile.get('initialTranscriptions')[this.$store.state.parts.documentId]
                  || this.$store.state.transcriptions.transcriptions[0].pk;
            this.selectedTranscription = tr;
        } catch (err) {
            console.log('couldnt fetch part data!', err);
        }

        document.addEventListener('keydown', function(event) {
            if (this.blockShortcuts) return;
            if (event.keyCode == 33 ||  // page up
                (event.keyCode == (this.readDirection == 'rtl'?39:37) && event.ctrlKey)) {  // arrow left

                this.getPrevious();
                event.preventDefault();
            } else if (event.keyCode == 34 ||   // page down
                       (event.keyCode == (this.readDirection == 'rtl'?37:39) && event.ctrlKey)) {  // arrow right
                this.getNext();
                event.preventDefault();
            }
        }.bind(this));

        let debounced = _.debounce(function() {  // avoid calling this too often
            if(this.$refs.segPanel) this.$refs.segPanel.refresh();
            if(this.$refs.visuPanel) this.$refs.visuPanel.refresh();
            if(this.$refs.diploPanel) this.$refs.diploPanel.refresh();
        }.bind(this), 200);
        window.addEventListener('resize', debounced);

        // catch background emited events when masks are recalculated
        let $alertsContainer = $('#alerts-container');
        $alertsContainer.on('part:mask', function(ev, data) {
            data.lines.forEach(function(lineData) {
                let line = this.$store.state.lines.all.find(l=>l.pk == lineData.pk);
                if (line) {  // might have been deleted in the meantime
                    line.mask = lineData.mask;
                }
            }.bind(this));
        }.bind(this));
    },
    methods: {
        async deleteTranscription(ev) {
            let transcription = ev.target.dataset.trpk;
            // I lied, it's only archived
            if(confirm("Are you sure you want to delete the transcription?")) {
                await this.$store.dispatch('transcriptions/archiveTranscription', transcription)
                ev.target.parentNode.remove();  // meh
                let compInd = this.comparedTranscriptions.findIndex(e=>e.pk == transcription);
                if (compInd != -1) Vue.delete(this.comparedTranscriptions, compInd)
            }
        },
        async getCurrentContent(transcription) {
            await this.$store.dispatch('transcriptions/fetchContent', transcription);
            this.$store.commit('lines/updateCurrentTrans', this.selectedTranscription);
        },
        getComparisonContent() {
            this.comparedTranscriptions.forEach(async function(tr, i) {
                if (tr != this.selectedTranscription) {
                    await this.$store.dispatch('transcriptions/fetchContent', tr);
                }
            }.bind(this));
        },
        async getPrevious(ev) {
            if (this.$store.state.parts.loaded && this.$store.state.parts.previous) {
                let documentId = this.$store.state.parts.documentId;
                let previous = this.$store.state.parts.previous;
                this.$store.commit('regions/reset');
                this.$store.commit('lines/reset');
                this.$store.commit('parts/reset');
                this.$store.commit('parts/setDocumentId', documentId);
                try {
                    await this.$store.dispatch('parts/fetchPart', previous);
                    this.getCurrentContent(this.selectedTranscription);
                    this.getComparisonContent();
                } catch (err) {
                    console.log('couldnt fetch part data!', err);
                }
            }
        },
        async getNext(ev) {
            if (this.$store.state.parts.loaded && this.$store.state.parts.next) {
                let documentId = this.$store.state.parts.documentId;
                let next = this.$store.state.parts.next;
                this.$store.commit('regions/reset');
                this.$store.commit('lines/reset');
                this.$store.commit('parts/reset');
                this.$store.commit('parts/setDocumentId', documentId);
                try {
                    await this.$store.dispatch('parts/fetchPart', next);
                    this.getCurrentContent(this.selectedTranscription);
                    this.getComparisonContent();
                } catch (err) {
                    console.log('couldnt fetch part data!', err);
                }
            }
        },
    }
}
</script>

<style scoped>
</style>