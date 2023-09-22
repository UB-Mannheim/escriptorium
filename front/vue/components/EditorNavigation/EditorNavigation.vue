<template>
    <nav class="escr-editor-nav">
        <div class="escr-editor-nav-left">
            <EscrBreadcrumbs
                :items="breadcrumbs"
            />
            <h1
                class="escr-element-title"
                :title="elementTitle"
            >
                {{ elementTitle }}
            </h1>
        </div>
        <div class="escr-editor-nav-right" />
    </nav>
</template>
<script>
import { mapState } from "vuex";
import EscrBreadcrumbs from "../Breadcrumbs/Breadcrumbs.vue";
import "./EditorNavigation.css";

export default {
    name: "EscrEditorNavigation",
    components: {
        EscrBreadcrumbs,
    },
    computed: {
        ...mapState({
            projectName: (state) => state.document.projectName,
            projectSlug: (state) => state.document.projectSlug,
            documentName: (state) => state.document.name,
            documentId: (state) => state.document.id,
            elementFilename: (state) => state.parts.filename,
            elementNumber: (state) => state.parts.order,
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
                        title: this.elementNumber ? `Element ${this.elementNumber}` : "Loading...",
                    },
                ];
            }
            return breadcrumbs;
        },
        elementTitle() {
            return (this.elementNumber && this.elementFilename)
                ? `Element ${this.elementNumber} – ${this.elementFilename}`
                : "Loading...";
        }
    }
}
</script>
