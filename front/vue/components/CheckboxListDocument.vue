<template>
    <input type="checkbox" class="checkbox-document-list" @click="appendDocument" ref="checkbox">
</template>

<script>
  export default {
  props: [
     'documentId',
  ],
  computed: {
    lastChecked() {
      return this.$store.state.documentslist.lastChecked;
    }
  },
  methods: {
    appendDocument(event){ 
      let id = parseInt($(this.$refs.checkbox).prop('id'));
      let checked = $(this.$refs.checkbox).prop('checked');
      let scope = this;
      this.$store.commit('documentslist/setCheckboxList', {'selected': this.documentId, 'bool': checked});
      if (event.shiftKey) {
        if (this.lastChecked) {
            let range = (id > this.lastChecked) ? new Array(this.lastChecked, id) : new Array(this.lastChecked, id);
            $('.checkbox-document-list').each(function(i, obj) {
              let item = $(this).prop('id');
              if(item > range[0] && item < range[1])
                $(this).prop('checked', true);
                scope.$store.commit('documentslist/setCheckboxList', {'selected': $(this).val(), 'bool': true});
            });
        }
      }
      let _lastChecked = (this.lastChecked && checked) ? this.lastChecked : $(this.$refs.checkbox).prop('id');
      scope.$store.commit('documentslist/setLastChecked', _lastChecked);
    }
  }
}
</script>
