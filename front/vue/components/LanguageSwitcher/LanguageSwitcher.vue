<template>
    <VMenu
        placement="right-end"
        theme="vertical-menu"
        :triggers="['click']"
    >
        <button
            :aria-label="'Switch language'"
            class="escr-globalnav-icon escr-language-switcher-btn"
            type="button"
        >
            <LanguageIcon />
            <span>{{ currentLang.toUpperCase() }}</span>
        </button>
        <template #popper>
            <ul class="escr-vertical-menu">
                <li v-for="lang in languages" :key="lang">
                    <a href="#" @click.prevent="select(lang)">{{ languageName(lang) }}</a>
                </li>
            </ul>
        </template>
    </VMenu>
</template>

<script>
import Cookies from "js-cookie";
import { Menu as VMenu } from "floating-vue";
import LanguageIcon from "../Icons/LanguageIcon/LanguageIcon.vue";

const LANGUAGE_NAMES = {
    en: "English",
    fr: "Français",
    de: "Deutsch",
    es: "Español",
    he: "עברית",
};

export default {
    name: "EscrLanguageSwitcher",
    components: {
        VMenu,
        LanguageIcon,
    },
    props: {
        setLanguageUrl: {
            type: String,
            required: true,
        },
        languages: {
            type: Array,
            required: true,
        },
    },
    data() {
        return {
            currentLang: document.documentElement.lang?.split("-")[0] || "en",
        };
    },
    methods: {
        languageName(code) {
            return LANGUAGE_NAMES[code] || code;
        },
        select(code) {
            const body = new URLSearchParams({
                language: code,
                next: window.location.pathname + window.location.search,
            });
            fetch(this.setLanguageUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-CSRFToken": Cookies.get("csrftoken"),
                },
                body: body.toString(),
                credentials: "same-origin",
            }).finally(() => {
                window.location.reload();
            });
        },
    },
};
</script>
