<template>
    <nav class="escr-editor-nav">
        <div class="escr-editor-nav-meta">
            <EscrBreadcrumbs
                :items="breadcrumbs"
            />
            <h1
                class="escr-element-title"
                :title="elementHeading"
            >
                {{ elementHeading }}
            </h1>
        </div>
        <div class="escr-editor-nav-actions">
            <VDropdown
                theme="escr-tooltip-small"
                placement="bottom"
                :distance="8"
                :triggers="['hover']"
            >
                <EscrButton
                    color="text"
                    :aria-label="`${getPrevOrNextString('left')} page`"
                    :on-click="() => loadPart(getPrevOrNextString('left'))"
                    :disabled="disabled || !hasPrevOrNextElement('left')"
                >
                    <template #button-icon>
                        <ArrowCircleLeftIcon />
                    </template>
                </EscrButton>
                <template #popper>
                    {{ getPrevOrNextTooltip('left') }}
                </template>
            </VDropdown>
            <VDropdown
                theme="escr-tooltip-small"
                placement="bottom"
                :distance="8"
                :triggers="['hover']"
            >
                <EscrButton
                    color="text"
                    :aria-label="`${getPrevOrNextString('right')} page`"
                    :on-click="() => loadPart(getPrevOrNextString('right'))"
                    :disabled="disabled || !hasPrevOrNextElement('right')"
                >
                    <template #button-icon>
                        <ArrowCircleRightIcon />
                    </template>
                </EscrButton>
                <template #popper>
                    {{ getPrevOrNextTooltip('right') }}
                </template>
            </VDropdown>
            <span
                v-if="partsCount"
                class="element-switcher"
            >
                <span>{{ elementNumber || "-" }}</span> / {{ partsCount }}
            </span>
            <VDropdown
                class="new-section with-separator"
                theme="escr-tooltip-small"
                placement="bottom"
                :distance="8"
                :triggers="['hover']"
            >
                <EscrButton
                    color="text"
                    aria-label="View Element Details"
                    :disabled="disabled"
                    :on-click="() => openModal('elementDetails')"
                >
                    <template #button-icon>
                        <InfoOutlineIcon />
                    </template>
                </EscrButton>
                <template #popper>
                    View Element Details
                </template>
            </VDropdown>
            <VDropdown
                theme="escr-tooltip-small"
                placement="bottom"
                :distance="8"
                :triggers="['hover']"
            >
                <EscrButton
                    color="text"
                    aria-label="Manage Ontology"
                    :disabled="disabled"
                    :on-click="() => openModal('ontology')"
                >
                    <template #button-icon>
                        <OntologyIcon />
                    </template>
                </EscrButton>
                <template #popper>
                    Ontology
                </template>
            </VDropdown>
            <VDropdown
                theme="escr-tooltip-small"
                placement="bottom"
                :distance="8"
                :triggers="['hover']"
            >
                <EscrButton
                    color="text"
                    aria-label="Manage Transcriptions"
                    :disabled="disabled"
                    :on-click="() => openModal('transcriptions')"
                >
                    <template #button-icon>
                        <TranscribeIcon />
                    </template>
                </EscrButton>
                <template #popper>
                    Transcriptions
                </template>
            </VDropdown>
        </div>
    </nav>
</template>
<script>
import { Dropdown as VDropdown } from "floating-vue";
import { mapActions, mapState } from "vuex";
import ArrowCircleLeftIcon from "../Icons/ArrowCircleLeftIcon/ArrowCircleLeftIcon.vue";
import ArrowCircleRightIcon from "../Icons/ArrowCircleRightIcon/ArrowCircleRightIcon.vue";
import EscrBreadcrumbs from "../Breadcrumbs/Breadcrumbs.vue";
import EscrButton from "../Button/Button.vue";
import InfoOutlineIcon from "../Icons/InfoOutlineIcon/InfoOutlineIcon.vue";
import OntologyIcon from "../Icons/OntologyIcon/OntologyIcon.vue";
import TranscribeIcon from "../Icons/TranscribeIcon/TranscribeIcon.vue";
import "./EditorNavigation.css";

export default {
    name: "EscrEditorNavigation",
    components: {
        ArrowCircleLeftIcon,
        ArrowCircleRightIcon,
        EscrBreadcrumbs,
        EscrButton,
        InfoOutlineIcon,
        OntologyIcon,
        TranscribeIcon,
        VDropdown,
    },
    props: {
        /**
         * True if all buttons and tools should be disabled
         */
        disabled: {
            type: Boolean,
            required: true,
        },
    },
    computed: {
        ...mapState({
            documentId: (state) => state.document.id,
            documentName: (state) => state.document.name,
            elementFilename: (state) => state.parts.filename,
            elementNumber: (state) => state.parts.order,
            elementTitle: (state) => state.parts.title,
            nextPart: (state) => state.parts.next,
            partsCount: (state) => state.document.partsCount,
            prevPart: (state) => state.parts.previous,
            projectName: (state) => state.document.projectName,
            projectSlug: (state) => state.document.projectSlug,
            readDirection: (state) => state.document.readDirection,
        }),
        breadcrumbs() {
            let breadcrumbs = [{ title: "Loading..." }];
            if (this.projectName && this.projectSlug && this.documentName && this.documentId) {
                breadcrumbs = [
                    { title: "My Projects", href: "/projects" },
                    {
                        title: this.projectName,
                        href: `/project/${this.projectSlug}`
                    },
                    {
                        title: this.documentName,
                        href: `/document/${this.documentId}`
                    },
                    {
                        title: "Images",
                        href: `/document/${this.documentId}/images`,
                    },
                    {
                        title: this.elementTitle ? this.elementTitle : "Loading...",
                    },
                ];
            }
            return breadcrumbs;
        },
        elementHeading() {
            return (this.elementTitle && this.elementFilename)
                ? `${this.elementTitle} – ${this.elementFilename}`
                : "Loading...";
        },
    },
    methods: {
        ...mapActions("parts", ["loadPart"]),
        ...mapActions("globalTools", ["openModal"]),
        hasPrevOrNextElement(direction) {
            if (direction === "left") {
                // left = next in RTL, previous in LTR
                return this.readDirection === "rtl" ? this.nextPart : this.prevPart;
            }else {
                // right = previous in RTL, next in LTR
                return this.readDirection === "rtl" ? this.prevPart : this.nextPart;
            }
        },
        getPrevOrNextString(direction) {
            if (direction === "left") {
                // left = next in RTL, previous in LTR
                return this.readDirection === "rtl" ? "next" : "previous";
            } else {
                // right = previous in RTL, next in LTR
                return this.readDirection === "rtl" ? "previous" : "next";
            }
        },
        getPrevOrNextTooltip(direction) {
            if (direction === "left") {
                // left = next in RTL, previous in LTR
                return this.readDirection === "rtl"
                    ? "Next Element (PgDn)"
                    : "Previous Element (PgUp)";
            } else {
                // right = previous in RTL, next in LTR
                return this.readDirection === "rtl"
                    ? "Previous Element (PgUp)"
                    : "Next Element (PgDn)";
            }
        },
    }
}
</script>
