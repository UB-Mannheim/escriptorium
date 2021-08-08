<template>
    <form method="GET">
        <ul class="p-0 ckeckbox-list list-unstyled">
            <li v-for="tag in tags" :key="tag.pk">
                <input type="checkbox" onchange="this.form.submit()" name="tags" v-bind:value="tag.name" v-if="setchecked(tag.name)" checked>
                <input type="checkbox" onchange="this.form.submit()" name="tags" v-bind:value="tag.name" v-else >
                <span class="badge" v-bind:style="{'background-color': tag.color}">{{tag.name}}</span>
            </li>
        </ul>
    </form>
</template>

<script>
  export default {
  props: [
     'tags',
     'filters',
  ],
  created: function() {
      this.$store.commit('documentslist/setDocTags', this.tags);
      this.$store.commit('documentslist/setFilters', this.filters);
  },
  methods: {
     setchecked(tag){ 
         return this.filters.includes(tag)
     }
  }
}

</script>
