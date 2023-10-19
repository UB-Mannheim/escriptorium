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
    return await axios.get("/projects/", { params });
};
// retrieve single project by ID
export const retrieveProject = async (projectId) =>
    await axios.get(`/projects/${projectId}/`);

// retrieve the list of all project tags across all projects
export const retrieveAllProjectTags = async () =>
    await axios.get("/tags/project/");

export const createProjectTag = async ({ name, color }) =>
    await axios.post("/tags/project/", {
        name,
        color,
    });

// create a project by providing a name (and optional other metadata)
export const createProject = async ({ name, guidelines, tags }) =>
    await axios.post("/projects/", {
        name,
        guidelines,
        tags,
    });

export const editProject = async (projectId, { name, guidelines, tags }) =>
    await axios.put(`/projects/${projectId}/`, {
        name,
        guidelines,
        tags,
    });

// delete a project by ID
export const deleteProject = async (projectId) =>
    await axios.delete(`/projects/${projectId}/`);

// retrieve a list of unique tags on all documents in a project
export const retrieveProjectDocumentTags = async (project_id) =>
    await axios.get(`/projects/${project_id}/tags/`);

// create a new Document-level tag on this project
export const createProjectDocumentTag = async ({ name, color, projectId }) =>
    await axios.post(`/projects/${projectId}/tags/`, {
        name,
        color,
    });

// share this project with a group or user
export const shareProject = async ({ projectId, group, user }) =>
    await axios.post(`/projects/${projectId}/share/`, {
        group,
        user,
    });
