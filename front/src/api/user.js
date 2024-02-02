import axios from "axios";

export const retrieveGroups = async () => await axios.get("/groups/");

export const retrieveCurrentUser = async () =>
    await axios.get("/users/current/");
