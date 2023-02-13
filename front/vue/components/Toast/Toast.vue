<template>
    <div
        :class="classes"
        aria-live="assertive"
        role="alert"
    >
        <span>
            {{ message }}
        </span>
        <EscrButton
            :on-click="onClose"
            aria-label="Close"
            color="text"
            size="small"
        >
            <template #button-icon>
                <XIcon />
            </template>
        </EscrButton>
    </div>
</template>
<script>
import EscrButton from "../Button/Button.vue";
import XIcon from "../Icons/XIcon/XIcon.vue";
import "./Toast.css";

export default {
    name: "EscrToast",
    components: { EscrButton, XIcon },
    props: {
        /**
         * The color of the toast alert, which must be one of `alert`, `success`, or `test`.
         */
        color: {
            type: String,
            default: "text",
            validator(value) {
                return [
                    "alert",
                    "success",
                    "text",
                ].includes(value);
            },
        },
        /**
         * By default, toasts will disappear after 2000 ms (2 seconds). Provide a number
         * here to change the delay, or pass 0 to disable auto-disappearance.
         */
        delay: {
            type: Number,
            default: 2000,
        },
        /**
         * The message to display for the toast alert.
         */
        message: {
            type: String,
            required: true,
        },
        /**
         * Callback that is called after `delay` ms, or by clicking the close button.
         */
        onClose: {
            type: Function,
            required: true,
        },
    },
    computed: {
        classes() {
            return {
                "escr-toast": true,
                [`escr-toast--${this.color}`]: true,
            };
        }
    },
    mounted() {
        if (this.delay) {
            setTimeout(this.onClose, this.delay);
        }
    }
}
</script>
