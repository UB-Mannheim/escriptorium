import axios from 'axios'

//const SCRIPT_NAME = process.env.ESC_SCRIPT_NAME;
const path_components = location.pathname.split("/documents/tasks", 2);
const SCRIPT_NAME = path_components[0];
console.log('documentstasks/api: SCRIPT_NAME=', SCRIPT_NAME);
console.log('href    =', location.href);
console.log('pathname=', location.pathname);

axios.defaults.baseURL = SCRIPT_NAME +  '/api'
axios.defaults.xsrfCookieName = 'csrftoken'
axios.defaults.xsrfHeaderName = 'X-CSRFToken'
axios.defaults.withCredentials = true

export const listDocumentsTasks = async (params) => (await axios.get('/documents/tasks/', { params }))

export const cancelDocumentTasks = async (id) => (await axios.post(`/documents/${id}/cancel_tasks/`))
