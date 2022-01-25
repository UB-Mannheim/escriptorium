<template>
  <div>
    <table class="table table-hover">
      <tr>
        <th>Name</th>
        <th>User</th>
        <th>Statistics</th>
        <th>Last task started</th>
      </tr>
      <template v-if="$store.state.documentsTasks">
        <Row
          v-for="documentTasks in $store.state.documentsTasks.results"
          :timezone="timezone"
          :document-tasks="documentTasks"
          :key="documentTasks.pk"
        />
      </template>
      <template v-else>
        <tr>
          <td>No document tasks to display.</td>
        </tr>
      </template>
    </table>
    <ul class="pagination justify-content-end">
      <li class="page-item">
        <template v-if="$store.state.documentsTasks && $store.state.documentsTasks.previous">
            <a class="page-link" @click="loadPrev()"><span aria-hidden="true">&#139;</span></a>
        </template>
      </li>
      <li class="page-item">
        <template v-if="$store.state.documentsTasks && $store.state.documentsTasks.next">
            <a class="page-link" @click="loadNext()"><span aria-hidden="true">&#155;</span></a>
        </template>
      </li>
    </ul>
  </div>
</template>

<script>
import Row from "./Row.vue";

export default {
  data() {
    return {
      currentPage: 1,
    }
  },
  components: {
    Row,
  },
  async created() {
    this.timezone = moment.tz.guess();
    this.getDocumentTasks();
  },
  methods: {
    loadPrev() {
        this.currentPage -= 1;
        this.getDocumentTasks();
    },
    loadNext() {
        this.currentPage += 1;
        this.getDocumentTasks();
    },
    async getDocumentTasks() {
      await this.$store.dispatch("fetchDocumentsTasks", this.currentPage);
    }
  }
};
</script>

<style scoped>
</style>