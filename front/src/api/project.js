import axios from "axios";
import { getFilterParams, getSortParam } from "./util";

// retrieve projects list
export const retrieveProjects = async ({ field, direction, filters }) => {
    let params = {};
    if (field && direction) {
        params.ordering = getSortParam({ field, direction });
    }
    if (filters) {
        params = { ...params, ...getFilterParams({ filters }) };
    }
    return await axios.get("/projects", { params });
};
// retrieve single project by ID
export const retrieveProject = async (projectId) =>
    await axios.get(`/projects/${projectId}`);

// retrieve the list of all project tags across all projects
export const retrieveAllProjectTags = async () =>
    await axios.get("/tags/project");

// create a project by providing a name
export const createProject = async (name) =>
    await axios.post("/projects", { params: { name } });

// delete a project by ID
export const deleteProject = async (projectId) =>
    await axios.delete(`/projects/${projectId}`);

// retrieve a list of unique tags on all documents in a project
export const retrieveProjectDocumentTags = async (project_id) =>
    await axios.get(`/projects/${project_id}/tags`);
