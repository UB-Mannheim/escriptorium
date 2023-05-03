import axios from "axios";

export const retrieveGroups = async () => await axios.get("/groups");
