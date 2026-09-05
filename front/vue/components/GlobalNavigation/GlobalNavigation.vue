<template>
    <nav class="escr-global-nav">
        <div class="escr-upper-navgroup">
            <a
                :href="url('/')"
                aria-label="eScriptorium"
            >
                <EscrLogo />
            </a>
            <VMenu
                v-if="isAuthenticated && !searchDisabled"
                placement="right-start"
                theme="vertical-menu"
                :triggers="['click']"
            >
                <button
                    v-if="isAuthenticated && !searchDisabled"
                    :href="url('/search/')"
                    :aria-label="$gettext('global search')"
                    class="escr-global-search"
                    :class="{
                        'escr-globalnav-icon': true,
                        'escr-globalnav-icon-active': ['/search/', '/find-replace/'].some(
                            (page) => location.href.endsWith(page)
                        ),
                    }"
                >
                    <SearchLargeIcon />
                    <span v-translate>Search</span>
                </button>

                <template #popper>
                    <ul class="escr-vertical-menu escr-tasks-menu">
                        <li>
                            <a :href="url('/search/')">
                                <span v-translate>Search</span>
                            </a>
                        </li>
                        <li>
                            <a :href="url('/find-replace/')">
                                <span v-translate>Find and Replace</span>
                            </a>
                        </li>
                    </ul>
                </template>
            </VMenu>
            <a
                v-if="isAuthenticated"
                :href="url('/projects/')"
                :aria-label="$gettext('projects list')"
                :class="{
                    'escr-globalnav-icon': true,
                    'escr-globalnav-icon-active': location.href.endsWith('/projects/'),
                }"
            >
                <HomeIcon />
                <span v-translate>Projects</span>
            </a>
            <a
                v-if="isAuthenticated"
                :href="url('/models/')"
                :aria-label="$gettext('models list')"
                :class="{
                    'escr-globalnav-icon': true,
                    'escr-globalnav-icon-active': location.href.endsWith('/models/'),
                }"
            >
                <ModelsIcon />
                <span v-translate>Models</span>
            </a>
            <a
                v-if="isAuthenticated"
                :href="url('/training/')"
                :aria-label="$gettext('training page')"
                :class="{
                    'escr-globalnav-icon': true,
                    'escr-globalnav-icon-active': location.href.endsWith('/training/'),
                }"
            >
                <TrainIcon />
                <span v-translate>Training</span>
            </a>
            <VMenu
                v-if="isAuthenticated"
                placement="right-start"
                theme="vertical-menu"
                :triggers="['click']"
            >
                <button
                    :aria-label="$gettext('expand task monitoring and usage menu')"
                    :class="{
                        'escr-globalnav-icon': true,
                        'escr-globalnav-icon-active': ['/tasks/', '/quotas/', '/downloads/'].some(
                            (page) => location.href.endsWith(page)
                        ),
                    }"
                    type="button"
                >
                    <TasksIcon />
                    <span v-translate>Tasks</span>
                </button>
                <template #popper>
                    <ul class="escr-vertical-menu escr-tasks-menu">
                        <li>
                            <a :href="url('/documents/tasks/')">
                                <span v-translate>Task Monitoring</span>
                            </a>
                        </li>
                        <li>
                            <a :href="url('/quotas/')">
                                <span v-translate>Task Usage</span>
                            </a>
                        </li>
                        <li>
                            <a :href="url('/downloads/')">
                                <span>Downloads</span>
                            </a>
                        </li>
                    </ul>
                </template>
            </VMenu>
        </div>
        <div class="escr-lower-navgroup">
            <VMenu
                v-if="isAuthenticated"
                placement="right-end"
                theme="vertical-menu"
                :triggers="['click']"
            >
                <button
                    :aria-label="$gettext('expand user profile menu')"
                    :class="{
                        'escr-globalnav-icon': true,
                        'escr-globalnav-icon-active': profilePages.some(
                            (page) => location.href.endsWith(page)
                        ),
                    }"
                    type="button"
                >
                    <ProfileIcon />
                    <span v-translate>Profile</span>
                </button>
                <template #popper>
                    <ul class="escr-vertical-menu">
                        <li>
                            <a :href="url('/profile/')">
                                <span v-translate>Profile Settings</span>
                            </a>
                        </li>
                        <li>
                            <a :href="url('/password_change/')">
                                <span v-translate>Change Password</span>
                            </a>
                        </li>
                        <li v-if="canInvite">
                            <a :href="url('/invite/')">
                                <span v-translate>Invite Users</span>
                            </a>
                        </li>
                        <li
                            v-if="isStaff"
                            class="new-section"
                        >
                            <a :href="url('/quotas/instance/')">
                                <span v-translate>Leaderboard</span>
                            </a>
                        </li>
                        <li v-if="isStaff">
                            <a :href="url('/admin/')">
                                <span v-translate>Site Administration</span>
                            </a>
                        </li>
                        <li class="new-section">
                            <a :href="url('/logout/')">
                                <span v-translate>Logout</span>
                            </a>
                        </li>
                    </ul>
                </template>
            </VMenu>
            <a
                v-else
                :href="url('/login/')"
                :aria-label="$gettext('sign in')"
                class="escr-globalnav-icon"
            >
                <ProfileIcon />
                <span v-translate>Sign in</span>
            </a>
            <LanguageSwitcher
                v-if="languages && languages.length > 1"
                class="escr-language-switcher"
                :set-language-url="setLanguageUrl"
                :languages="languages"
            />
            <input
                id="escr-lightdark-switcher"
                type="checkbox"
                :aria-label="$gettext('switch to light mode')"
                :checked="currentTheme === 'dark-mode'"
                @change="toggleTheme"
            >
            <label
                for="escr-lightdark-switcher"
            >
                <DarkModeIcon v-if="currentTheme === 'dark-mode'" />
                <LightModeIcon v-else />
            </label>
        </div>
    </nav>
</template>
<script>
import { Menu as VMenu } from "floating-vue";
import DarkModeIcon from "../Icons/DarkModeIcon/DarkModeIcon.vue";
import EscrLogo from "../Icons/EscrLogo/EscrLogo.vue";
import HomeIcon from "../Icons/HomeIcon/HomeIcon.vue";
import LanguageSwitcher from "../LanguageSwitcher/LanguageSwitcher.vue";
import LightModeIcon from "../Icons/LightModeIcon/LightModeIcon.vue";
import ModelsIcon from "../Icons/ModelsIcon/ModelsIcon.vue";
import ProfileIcon from "../Icons/ProfileIcon/ProfileIcon.vue";
import SearchLargeIcon from "../Icons/SearchLargeIcon/SearchLargeIcon.vue";
import TasksIcon from "../Icons/TasksIcon/TasksIcon.vue";
import TrainIcon from "../Icons/TrainIcon/TrainIcon.vue";
import "../VerticalMenu/VerticalMenu.css";
import "./GlobalNavigation.css";
import { mapActions, mapState } from "vuex";
import { SCRIPT_NAME } from '../../../src/scriptname.js';

export default {
    name: "EscrGlobalNavigation",
    components: {
        DarkModeIcon,
        EscrLogo,
        HomeIcon,
        LanguageSwitcher,
        LightModeIcon,
        ModelsIcon,
        ProfileIcon,
        SearchLargeIcon,
        TasksIcon,
        TrainIcon,
        VMenu,
    },
    props: {
        isAuthenticated: {
            type: Boolean,
            required: true,
        },
        searchDisabled: {
            type: Boolean,
            required: true,
        },
        setLanguageUrl: {
            type: String,
            required: true,
        },
        languages: {
            type: Array,
            default: null,
        },
    },
    data() {
        return {
            currentTheme: "light-mode",
        };
    },
    computed: {
        ...mapState({
            canInvite: (state) => state.user.canInvite,
            isStaff: (state) => state.user.isStaff,
        }),
        location() {
            // helper to access window object from within template
            return window.location;
        },
        profilePages() {
            // pages that will trigger the "profile" button to be in the active state
            return ["/profile/", "/password_change/", "/invite/", "/quotas/instance/"];
        },
    },
    mounted() {
        const initTheme = this.getTheme() || this.getMediaPreference();
        this.setTheme(initTheme);
        if (this.isAuthenticated) {
            this.fetchCurrentUser();
        }
    },
    methods: {
        ...mapActions("user", [
            "fetchCurrentUser",
        ]),
        url(addr) {
            return SCRIPT_NAME + addr;
        },
        getTheme() {
            return localStorage.getItem("user-theme");
        },
        getMediaPreference() {
            const hasDarkPreference = window.matchMedia(
                "(prefers-color-scheme: dark)"
            ).matches;
            if (hasDarkPreference) {
                return "dark-mode";
            } else {
                return "light-mode";
            }
        },
        setTheme(theme) {
            localStorage.setItem("user-theme", theme);
            this.currentTheme = theme;
            document.documentElement.className = theme;
        },
        /** Callback to toggle light/dark theme. */
        toggleTheme() {
            const activeTheme = localStorage.getItem("user-theme");
            if (activeTheme === "light-mode") {
                this.setTheme("dark-mode");
            } else {
                this.setTheme("light-mode");
            }
        }

    }
}
</script>
