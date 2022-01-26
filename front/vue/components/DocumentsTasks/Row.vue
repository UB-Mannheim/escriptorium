<template>
  <tr>
    <td>{{ documentTasks.name }}</td>
    <td>{{ documentTasks.owner }}</td>
    <td>{{ documentTasks.tasks_stats | formatStats }}</td>
    <td>{{ documentTasks.last_started_task | formatDate(timezone) }}</td>
  </tr>
</template>

<script>
export default {
  props: [
    'documentTasks',
    'timezone'
  ],
  filters: {
    formatDate(rawDate, timezone) {
      if (!rawDate) return "/";
      return moment.tz(rawDate, timezone).fromNow();
    },
    formatStats(rawStats) {
      if (!rawStats) return "/";
      const allStrings = Object.entries(rawStats).map((stat) => stat[1] !== 0 ? `${stat[1]} ${stat[0].toLowerCase()}` : null)
      const filteredStrings = allStrings.filter(val => val)
      return filteredStrings.join(", ")
    },
  },
};
</script>

<style scoped>
</style>