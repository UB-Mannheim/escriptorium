<template>
    <VMenu
        :delay="{ show: 0, hide: 20 }"
        theme="vertical-menu"
        placement="bottom-end"
        :shown="isOpen"
        :triggers="[]"
        :auto-hide="true"
        @apply-hide="closeMenu"
    >
        <EscrButton
            size="small"
            color="text"
            round
            :on-click="openMenu"
            :disabled="disabled"
        >
            <template #button-icon>
                <VerticalMenuIcon />
            </template>
        </EscrButton>
        <template #popper>
            <ul class="escr-vertical-menu">
                <li
                    v-for="item in items"
                    :key="item.key"
                    :class="item.class"
                >
                    <button
                        v-if="item.onClick"
                        @mousedown="item.onClick"
                    >
                        <component
                            :is="item.icon"
                            v-if="item.icon"
                            class="escr-menuitem-icon"
                        />
                        <span>
                            {{ item.label }}
                        </span>
                    </button>
                    <a
                        v-else-if="item.href"
                        :href="item.href"
                    >
                        <component
                            :is="item.icon"
                            v-if="item.icon"
                            class="escr-menuitem-icon"
                        />
                        <span>
                            {{ item.label }}
                        </span>
                    </a>
                </li>
            </ul>
        </template>
    </VMenu>
</template>
<script>
import { Menu as VMenu } from "floating-vue";
import EscrButton from "../../components/Button/Button.vue";
import VerticalMenuIcon from "../../components/Icons/VerticalMenuIcon/VerticalMenuIcon.vue";
import "./VerticalMenu.css";

export default {
    name: "EscrVerticalMenu",
    components: {
        EscrButton,
        VerticalMenuIcon,
        VMenu,
    },
    props: {
        /**
         * Callback for closing the vertical menu.
         */
        closeMenu: {
            type: Function,
            required: true,
        },
        /**
         * Boolean indicating if the "open menu" button should be disabled.
         */
        disabled: {
            type: Boolean,
            default: false,
        },
        /**
         * Boolean indicating if the menu is currently open.
         */
        isOpen: {
            type: Boolean,
            default: false,
        },
        /**
         * List of menu items, which should each meet the following spec:
         * {
         *    class?: String,
         *    href?: String,
         *    icon?: Component,
         *    key: String,
         *    label: String,
         *    onClick?: Function,
         * }
         * and must have one of either onClick or href.
         */
        items: {
            type: Array,
            default: () => [],
            validator: (value) => {
                return value.every((item) => item.key && item.label && (item.onClick || item.href));
            },
        },
        /**
         * Callback for opening the vertical menu.
         */
        openMenu: {
            type: Function,
            required: true,
        },
    }
}
</script>
