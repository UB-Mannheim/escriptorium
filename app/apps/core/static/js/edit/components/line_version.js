var LineVersion = Vue.extend({
    props: ['version'],
    created() {
        this.timeZone = moment.tz.guess();
    },
    computed: {
        momentDate() {
            return moment.tz(this.version.created_at, this.timeZone);
        }
    },
    methods: {
        loadState() {
            this.$parent.$emit('update:transcription:version', this.version);
        }
    }
});