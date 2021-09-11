<template>
    <input type="checkbox" v-on:change="selectAllDocuments" ref="checkboxall">
</template>

<script>
  export default {
  props: [
     'documentId',
  ],
  methods: {
    selectAllDocuments(){
        let checked = $(this.$refs.checkboxall).prop('checked');
        let scope = this;
        $('.checkbox-document-list').each(function(i, obj) {
            $(this).prop('checked', checked);
            scope.$store.commit('documentslist/setCheckboxList', {'selected': $(this).val(), 'bool': checked});
        });
    }
  }
}
</script>
