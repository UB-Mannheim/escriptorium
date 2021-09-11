<template>
    <input type="checkbox" class="checkbox-document-list" @click="appendDocument" ref="checkbox">
</template>

<script>
  export default {
  props: [
     'documentId',
  ],
  methods: {
    appendDocument(){ 
      let checked = $(this.$refs.checkbox).prop('checked');
      this.$store.commit('documentslist/setCheckboxList', {'selected': this.documentId, 'bool': checked});
    }
  }
}
</script>
