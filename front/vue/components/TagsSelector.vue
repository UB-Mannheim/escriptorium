<template>
    <form method="GET">
        <ul class="p-0 ckeckbox-list list-unstyled">
            <li v-for="tag in tagList" :key="tag.pk">
                <input type="checkbox" onchange="this.form.submit()" name="tags" v-bind:value="tag.name" :checked="isChecked(tag.name)">
                <span class="badge" v-bind:style="{'background-color': tag.color}">{{ tag.name | truncate(10) }}</span>
            </li>
        </ul>
    </form>
</template>

<script>
  export default {
  props: [
     'tags',
     'filters',
     'documents',
  ],
  data () {
    return {
      tagList: []
    }
  },
  created(){
    this.$store.commit('documentslist/setAllProjectTags', this.tags);
    this.$store.commit('documentslist/setDocumentsId', this.documents);
    this.$store.dispatch('documentslist/buildTagsList');
  },
  methods: {
    isChecked(tag){ 
        return this.filters.includes(tag)
    }
  },
  filters: {
    truncate(value, num) {
        return value.slice(0, num) + (num < value.length ? '...' : '')
    }
  },
  watch: {
    "$store.state.documentslist.allProjectTags": {
      handler: function(nv) {
        this.tagList = nv;
      },
      immediate: true
    }
  }
}

</script>
