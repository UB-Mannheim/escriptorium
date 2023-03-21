<template>
    <div class="escr-sidebar-container">
        <div
            v-if="selectedKey"
            class="escr-modal-backdrop escr-sidebar-backdrop"
        />
        <div
            v-if="selectedKey"
            class="escr-selected-action"
        >
            <div class="escr-action-header">
                <component
                    :is="selectedAction.icon"
                    v-if="selectedAction.icon"
                    class="escr-action-icon"
                />
                <h2>{{ selectedAction.label }}</h2>
                <button
                    class="escr-close-action"
                    :aria-label="`Close the ${selectedAction.label} panel`"
                    @click="() => toggleAction(selectedAction.key)"
                >
                    <EscrXIcon />
                </button>
            </div>
            <component
                :is="selectedAction.panel"
                v-if="selectedKey"
                class="escr-action-panel"
                :data="selectedAction.data"
            />
        </div>
        <nav class="escr-sidebar">
            <ul>
                <li
                    v-for="action in actions"
                    :key="action.key"
                >
                    <button
                        :class="classes(action.key)"
                        :disabled="loading"
                        :aria-label="`Open the ${action.label} panel`"
                        @click="() => toggleAction(action.key)"
                    >
                        <component
                            :is="action.icon"
                            v-if="action.icon"
                        />
                        <span>{{ action.label }}</span>
                    </button>
                </li>
            </ul>
        </nav>
    </div>
</template>
<script>
import { mapActions, mapState } from "vuex";
import EscrXIcon from "../Icons/XIcon/XIcon.vue";
import "../Modal/Modal.css";
import "./Sidebar.css";

export default {
    name: "EscrSidebar",
    components: { EscrXIcon },
    props: {
        /**
         * A list of sidebar items, each of which should have a unique key (string),
         * a label (string), a panel (component), and optionally an icon (component)
         * and data (object).
         */
        actions: {
            type: Array,
            required: true,
            validator(value) {
                return Array.isArray(value) && value.every(
                    (v) => [
                        "key", "label", "panel",
                    ].every((prop) => Object.hasOwn(v, prop))
                );
            }
        },
        /**
         * A boolean indicating whether or not loading is occurring.
         */
        loading: {
            type: Boolean,
            default: false,
        },
    },
    computed: {
        ...mapState({
            selectedKey: (state) => state.sidebar.selectedAction,
        }),
        /**
         * Helper method to get the currently-selected action object.
         */
        selectedAction() {
            return this.actions.find((action) => action.key === this.selectedKey);
        },
    },
    methods: {
        ...mapActions("sidebar",
            [
                "toggleAction",
            ],
        ),
        classes(key) {
            return {
                "escr-sidebar-button": true,
                "escr-sidebar-button--selected": this.selectedKey === key,
            }
        },
    }
}
</script>
