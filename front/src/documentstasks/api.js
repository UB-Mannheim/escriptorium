import axios from "axios";

axios.defaults.baseURL = "/api";
axios.defaults.xsrfCookieName = "csrftoken";
axios.defaults.xsrfHeaderName = "X-CSRFToken";
axios.defaults.withCredentials = true;

export const listDocumentsTasks = async (params) =>
    await axios.get("/documents/tasks/", { params });

export const cancelDocumentTasks = async (id) =>
    await axios.post(`/documents/${id}/cancel_tasks/`);
