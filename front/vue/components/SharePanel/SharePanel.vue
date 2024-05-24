<template>
    <div>
        <div
            v-if="data && data.groups && data.groups.length"
            class="escr-share-list"
        >
            <h3>Groups</h3>
            <ul>
                <li
                    v-for="group in data.groups"
                    :key="group.pk"
                >
                    {{ group.name }}
                </li>
            </ul>
        </div>
        <div
            v-if="data && data.users && data.users.length"
            class="escr-share-list"
        >
            <h3>Users</h3>
            <ul>
                <li
                    v-for="user in data.users"
                    :key="user.pk"
                >
                    {{ getName(user) }}
                </li>
            </ul>
        </div>
        <EscrButton
            :on-click="(data && data.openShareModal) || (() => {})"
            :disabled="data && data.disabled"
            label="Add Group or User"
            size="small"
            color="outline-primary"
        >
            <template #button-icon>
                <EscrPlusIcon />
            </template>
        </EscrButton>
    </div>
</template>
<script>
import EscrButton from "../Button/Button.vue";
import EscrPlusIcon from "../Icons/PlusIcon/PlusIcon.vue";
import "./SharePanel.css";

export default {
    name: "EscrSharePanel",
    components: { EscrButton, EscrPlusIcon },
    props: {
        /**
         * Data for the share panel, an object containing users, groups, disabled boolean,
         * and a callback function openShareModal that should handle clicking "Add group or user".
         */
        data: {
            type: Object,
            required: true,
        },
    },
    methods: {
        /**
         * Helper method to get the user's first name and last name joined by a space, or fallback
         * to the username if not available.
         */
        getName(user) {
            const name = [user["first_name"], user["last_name"]].join(" ");
            return name.trim() || user.username;
        },
    },
}
</script>
