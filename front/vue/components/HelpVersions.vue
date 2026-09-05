<template>
    <p
        style="direction:ltr"
        v-html="helpText"
    ></p>
</template>

<script>
export default {
    computed: {
        helpText() {
            return this.$gettext(`Each line corresponds to an edition of the content, in inverse chronological order (Most recent at the top).
<br>The colors represent the difference with the previous version,
<br><font color="green">green</font> are <b>additions</b> while <font color="red">red</font> are <b>deletions</b>,
<br>meaning red characters are not actually part of the line anymore, they are displayed to easily spot the differences.
<br>You can mouse over the text to see the actual content.
<br>The load state button <i class="fas fa-file-upload" /> simply revert the content of the line to the corresponding text version.`);
        },
    },
};
</script>

<style scoped>
</style>
