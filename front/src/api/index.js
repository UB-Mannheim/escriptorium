import axios from "axios";
import { SCRIPT_NAME } from '../scriptname.js';

axios.defaults.baseURL = SCRIPT_NAME +  '/api'
axios.defaults.xsrfCookieName = "csrftoken";
axios.defaults.xsrfHeaderName = "X-CSRFToken";
axios.defaults.withCredentials = true;

export * from "./document";
export * from "./documentPart";
export * from "./project";
export * from "./scripts";
export * from "./user";
