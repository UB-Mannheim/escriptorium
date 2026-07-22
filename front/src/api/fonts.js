import axios from "axios";

export const retrieveFonts = async () => await axios.get("/fonts/");
