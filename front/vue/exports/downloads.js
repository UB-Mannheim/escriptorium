import Vue from "vue";
import axios from "axios";
import Downloads from "../pages/Downloads/Downloads.vue";

// Match the auth / CSRF defaults the rest of the app uses. Without these,
// same-origin DELETE / POST calls get rejected as CSRF failures.
axios.defaults.xsrfCookieName = "csrftoken";
axios.defaults.xsrfHeaderName = "X-CSRFToken";
axios.defaults.withCredentials = true;

new Vue({
    el: "#vue-downloads",
    components: { Downloads },
    render: (h) => h(Downloads),
});
