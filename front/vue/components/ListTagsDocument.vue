<template>
    <div class="d-inline-flex">
        <div v-for="tag in tags" :key="tag.pk" v-bind:value="tag.pk">
            <span class="badge m-1" v-bind:title="tag.name" v-bind:style="'background-color:' + tag.color">{{ tag.name | truncate(10) }}</span>
        </div>
    </div>
</template>

<script>

export default {
    props: [
        'documentId',
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
    filters: {
        truncate(value, num) {
            return value.slice(0, num) + (num < value.length ? '...' : '')
        }
    },
    watch: {
        "$store.state.documentslist.TagsListPerDocument": {
            handler: function(nv) {
                let newTags = this.allTagsList.filter(obj => this.tagList[this.documentId].includes(obj.pk));
                this.tags = newTags;
            },
            immediate: false
        }
    }
}
</script>

<style scoped>
</style>