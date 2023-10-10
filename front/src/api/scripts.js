import axios from "axios";

export const retrieveScripts = async () => await axios.get("/scripts/");
