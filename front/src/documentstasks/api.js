import axios from 'axios'


axios.defaults.baseURL = '/api'
axios.defaults.xsrfCookieName = 'csrftoken'
axios.defaults.xsrfHeaderName = 'X-CSRFToken'
axios.defaults.withCredentials = true

export const listDocumentsTasks = async (page) => (await axios.get(`/documents/tasks/?page=${page}`))
