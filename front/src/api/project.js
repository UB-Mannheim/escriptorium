import axios from "axios";

export const retrieveProjects = async ({ field, direction, filters }) => {
    let params = {};
    if (field && direction && direction !== 0) {
        params.ordering = field;
        if (direction == -1) {
            params.ordering = `-${field}`;
        }
    }
    if (filters) {
        filters.forEach((filter) => {
            params[filter.type] = filter.value;
            if (filter.operator) params[`${filter.type}_op`] = filter.operator;
        });
    }
    return await axios.get("/projects", { params });
};
export const createProject = async (name) =>
    await axios.post("/projects", { params: { name } });
export const retrieveProject = async (projectId) =>
    await axios.get(`/projects/${projectId}`);
export const retrieveAllProjectTags = async () =>
    await axios.get("/tags/project");
export const deleteProject = async (projectId) =>
    await axios.delete(`/projects/${projectId}`);
