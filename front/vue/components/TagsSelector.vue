<template>
    <form method="GET">
        <ul class="p-0 ckeckbox-list list-unstyled">
            <li
                v-for="tag in tagList"
                :key="tag.pk"
            >
                <input
                    type="checkbox"
                    onchange="this.form.submit()"
                    name="tags"
                    :value="tag.name"
                    :checked="isChecked(tag.name)"
                >
                <span
                    class="badge"
                    :style="{'background-color': tag.color}"
                >{{ tag.name | truncate(10) }}</span>
            </li>
        </ul>
    </form>
</template>

<script>
export default {
    filters: {
        truncate(value, num) {
            return value.slice(0, num) + (num < value.length ? "..." : "")
        }
    },
    props: [
        "tags",
        "filters",
        "tagsperdocuments",
    ],
    data () {
        return {
            tagList: []
        }
    },
    watch: {
        "$store.state.documentslist.allProjectTags": {
            handler: function(nv) {
                this.tagList = nv;
            },
            immediate: true
        }
    },
    created(){
        this.$store.commit("documentslist/setTagsListPerDocument", {docTags: this.splitNested(this.tagsperdocuments.split("¤")), update: true});
        this.$store.commit("documentslist/setAllProjectTags", this.tags);

    },
    methods: {
        isChecked(tag){
            return this.filters.includes(tag)
        },
        splitNested(data){
            const toNumbers = (arr) => arr.map(Number);
            var elements = [];
            for (let i = 0; i < data.length; i++){
                let items = data[i].split(";");
                elements.push({"pk": parseInt(items[0]), "tags": ((items[1]) ? toNumbers(items[1].split(",")) : [])});
            }
            return elements;
        }
    }
}

</script>
