import axios from "axios";

axios.defaults.baseURL = "/api";
axios.defaults.xsrfCookieName = "csrftoken";
axios.defaults.xsrfHeaderName = "X-CSRFToken";
axios.defaults.withCredentials = true;

export * from "./document";
export * from "./documentPart";
export * from "./project";
export * from "./scripts";
export * from "./user";
