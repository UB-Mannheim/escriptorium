<template>
    <nav class="escr-global-nav">
        <a href="/">
            <EscrLogo />
        </a>
    </nav>
</template>
<script>
import EscrLogo from "../Icons/EscrLogo/EscrLogo.vue";
import "./GlobalNavigation.css";
export default {
    name: "EscrGlobalNavigation",
    components: { EscrLogo }
}
</script>
