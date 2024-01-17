<template>
    <div class="d-inline-flex">
        <div
            v-for="tag in tags"
            :key="tag.pk"
            :value="tag.pk"
        >
            <span
                class="badge m-1"
                :title="tag.name"
                :style="'background-color:' + tag.color"
            >{{ tag.name | truncate(10) }}</span>
        </div>
    </div>
</template>

<script>

export default {
    filters: {
        truncate(value, num) {
            return value.slice(0, num) + (num < value.length ? "..." : "")
        }
    },
    props: [
        "documentId",
    ],
    data () {
        return {
            tags: []
        }
    },
    computed: {
        tagList() {
            return this.$store.state.documentslist.TagsListPerDocument;
        },
        allTagsList() {
            return this.$store.state.documentslist.allProjectTags;
        }
    },
    watch: {
        "$store.state.documentslist.TagsListPerDocument": {
            handler: function(nv) {
                this.refreshTagsList();
            },
            immediate: false,
            deep: true
        },
        allTagsList: {
            handler: function(newValue) {
                this.refreshTagsList();
            },
            deep: true
        }
    },
    mounted(){
        this.refreshTagsList();
    },
    methods: {
        refreshTagsList() {
            const index = this.tagList.findIndex((doc) => doc.pk == this.documentId);
            if(index > -1){
                let newTags = this.allTagsList.filter((obj) => this.tagList[index].tags.includes(obj.pk));
                this.tags = newTags;
            }
        }
    }
}
</script>

<style scoped>
</style>
