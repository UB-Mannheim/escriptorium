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
            return this.$gettext(`Each line is a different transcription as checked in the transcription management window <i class="fas fa-cog" />
<br>The colors represent the difference with the current transcription,
<br><font color="green">green</font> characters are not present in the current (editable) transcription while <font color="red">red</font> characters are not present in the compared transcription.`);
        },
    },
};
</script>

<style scoped>
</style>
