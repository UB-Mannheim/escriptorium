import axios from 'axios'

const path_components = location.pathname.split("/", 2);
const prefix = path_components[1];
const SCRIPT_NAME = (prefix.length > 0 ? "/" + prefix : "")

axios.defaults.baseURL = SCRIPT_NAME +  '/api'
axios.defaults.xsrfCookieName = 'csrftoken'
axios.defaults.xsrfHeaderName = 'X-CSRFToken'
axios.defaults.withCredentials = true

export const listDocumentsTasks = async (params) => (await axios.get('/documents/tasks/', { params }))

export const cancelDocumentTasks = async (id) => (await axios.post(`/documents/${id}/cancel_tasks/`))
