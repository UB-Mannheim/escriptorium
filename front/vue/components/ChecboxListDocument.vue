<template>
    <input type="checkbox" class="checkbox-document-list" @click="appendDoccument" ref="checkbox">
</template>

<script>
  export default {
  props: [
     'documentId',
  ],
  methods: {
    appendDoccument(){ 
      let id = $(this.$refs.checkbox).attr('document_id');
      let checked = $(this.$refs.checkbox).prop('checked');
      this.$store.commit('documentslist/setCheckboxList', {'selected': id, 'bool': checked});
    }
  }
}
</script>
