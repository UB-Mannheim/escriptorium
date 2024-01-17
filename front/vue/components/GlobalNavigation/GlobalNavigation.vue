<template>
    <nav class="escr-global-nav">
        <div class="escr-upper-navgroup">
            <a
                href="/"
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
                    href="/search/"
                    aria-label="global search"
                    class="escr-global-search"
                    :class="{
                        'escr-globalnav-icon': true,
                        'escr-globalnav-icon-active': ['/search/', '/find-replace/'].some(
                            (page) => location.href.endsWith(page)
                        ),
                    }"
                >
                    <SearchLargeIcon />
                    <span>Search</span>
                </button>

                <template #popper>
                    <ul class="escr-vertical-menu escr-tasks-menu">
                        <li>
                            <a href="/search/">
                                <span>Search</span>
                            </a>
                        </li>
                        <li>
                            <a href="/find-replace/">
                                <span>Find and Replace</span>
                            </a>
                        </li>
                    </ul>
                </template>
            </VMenu>
            <a
                v-if="isAuthenticated"
                href="/projects/"
                aria-label="projects list"
                :class="{
                    'escr-globalnav-icon': true,
                    'escr-globalnav-icon-active': location.href.endsWith('/projects/'),
                }"
            >
                <HomeIcon />
                <span>Projects</span>
            </a>
            <a
                v-if="isAuthenticated"
                href="/models/"
                aria-label="models list"
                :class="{
                    'escr-globalnav-icon': true,
                    'escr-globalnav-icon-active': location.href.endsWith('/models/'),
                }"
            >
                <ModelsIcon />
                <span>Models</span>
            </a>
            <VMenu
                v-if="isAuthenticated"
                placement="right-start"
                theme="vertical-menu"
                :triggers="['click']"
            >
                <button
                    aria-label="expand task monitoring and usage menu"
                    :class="{
                        'escr-globalnav-icon': true,
                        'escr-globalnav-icon-active': ['/tasks/', '/quotas/'].some(
                            (page) => location.href.endsWith(page)
                        ),
                    }"
                    type="button"
                >
                    <TasksIcon />
                    <span>Tasks</span>
                </button>
                <template #popper>
                    <ul class="escr-vertical-menu escr-tasks-menu">
                        <li>
                            <a href="/documents/tasks/">
                                <span>Task Monitoring</span>
                            </a>
                        </li>
                        <li>
                            <a href="/quotas/">
                                <span>Task Usage</span>
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
                    aria-label="expand user profile menu"
                    :class="{
                        'escr-globalnav-icon': true,
                        'escr-globalnav-icon-active': profilePages.some(
                            (page) => location.href.endsWith(page)
                        ),
                    }"
                    type="button"
                >
                    <ProfileIcon />
                    <span>Profile</span>
                </button>
                <template #popper>
                    <ul class="escr-vertical-menu">
                        <li>
                            <a href="/profile/">
                                <span>Profile Settings</span>
                            </a>
                        </li>
                        <li>
                            <a href="/password_change/">
                                <span>Change Password</span>
                            </a>
                        </li>
                        <li v-if="canInvite">
                            <a href="/invite/">
                                <span>Invite Users</span>
                            </a>
                        </li>
                        <li
                            v-if="isStaff"
                            class="new-section"
                        >
                            <a href="/quotas/instance/">
                                <span>Leaderboard</span>
                            </a>
                        </li>
                        <li v-if="isStaff">
                            <a href="/admin/">
                                <span>Site Administration</span>
                            </a>
                        </li>
                        <li class="new-section">
                            <a href="/logout/">
                                <span>Logout</span>
                            </a>
                        </li>
                    </ul>
                </template>
            </VMenu>
            <a
                v-else
                href="/login"
                aria-label="sign in"
                class="escr-globalnav-icon"
            >
                <ProfileIcon />
                <span>Sign in</span>
            </a>
            <input
                id="escr-lightdark-switcher"
                type="checkbox"
                aria-label="switch to light mode"
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
import LightModeIcon from "../Icons/LightModeIcon/LightModeIcon.vue";
import ModelsIcon from "../Icons/ModelsIcon/ModelsIcon.vue";
import ProfileIcon from "../Icons/ProfileIcon/ProfileIcon.vue";
import SearchLargeIcon from "../Icons/SearchLargeIcon/SearchLargeIcon.vue";
import TasksIcon from "../Icons/TasksIcon/TasksIcon.vue";
import "../VerticalMenu/VerticalMenu.css";
import "./GlobalNavigation.css";
import { mapActions, mapState } from "vuex";

export default {
    name: "EscrGlobalNavigation",
    components: {
        EscrLogo,
        DarkModeIcon,
        HomeIcon,
        LightModeIcon,
        ModelsIcon,
        ProfileIcon,
        SearchLargeIcon,
        TasksIcon,
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
