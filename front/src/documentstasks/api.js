import axios from 'axios'

import { SCRIPT_NAME } from '../scriptname.js';

axios.defaults.baseURL = SCRIPT_NAME +  '/api'
axios.defaults.xsrfCookieName = 'csrftoken'
axios.defaults.xsrfHeaderName = 'X-CSRFToken'
axios.defaults.withCredentials = true

export const listDocumentsTasks = async (params) => (await axios.get('/documents/tasks/', { params }))

export const cancelDocumentTasks = async (id) => (await axios.post(`/documents/${id}/cancel_tasks/`))
