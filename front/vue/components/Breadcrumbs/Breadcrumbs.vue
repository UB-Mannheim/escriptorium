<template>
    <ul class="escr-breadcrumbs">
        <li
            v-for="(item, index) in items"
            :key="`breadcrumb-${index}`"
            :class="index === 0 ? 'escr-first-crumb' : ''"
        >
            <a
                v-if="index !== items.length - 1 && item.href"
                :href="item.href"
            >
                {{ item.title }}
            </a>
            <span v-else>{{ item.title }}</span>
        </li>
    </ul>
</template>
<script>
import "./Breadcrumbs.css";

export default {
    name: "EscrBreadcrumbs",
    props: {
        items: {
            type: Array,
            required: true,
        }
    }
}

</script>
