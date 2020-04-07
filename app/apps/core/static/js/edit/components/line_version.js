const LineVersion = Vue.extend({
  props: ['version', 'previous'],
  created() {
    this.timeZone = moment.tz.guess();
  },
  computed: {
    momentDate() {
      return moment.tz(this.version.created_at, this.timeZone).calendar();
    },
    versionContent() {
      if (this.version.data) {
        return this.version.data.content;
      }
    },
    versionCompare() {
      if (this.version.data) {
        if (!this.previous) return this.version.data.content;
        let diff = Diff.diffChars(this.previous.data.content, this.version.data.content);
        return diff.map(function(part){
          let color = part.added ? 'green' :
                      part.removed ? 'red' : '';
          if (part.removed) {
            return '<small><font color="'+color+'" class="collapse show history-deletion">-'+part.value+'</font></small>';
          } else if (part.added) {
            return '<font color="'+color+'">'+part.value+'</font>';
          } else {
            return part.value;
          }
        }.bind(this)).join('');
      }
    }
  },
  methods: {
    loadState() {
      this.$parent.$emit('update:transcription:version', this.version);
    },
  }
});
