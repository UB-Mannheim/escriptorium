import axios from "axios";
import { getFilterParams, getSortParam, ontologyMap } from "./util";

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

// retrieve types list for a specific project
export const retrieveProjectOntology = async ({
    projectId,
    category,
    sortField,
    sortDirection,
}) => {
    let params = {};
    if (sortField && sortDirection) {
        params.ordering = getSortParam({
            field: sortField,
            direction: sortDirection,
        });
    }
    return await axios.get(
        `/projects/${projectId}/types/${ontologyMap[category]}`,
        { params },
    );
};

// retrieve characters, sorted by character or frequency, in all transcriptions in the project
export const retrieveProjectCharacters = async ({ projectId, field, direction }) => {
    let params = {};
    if (field && direction) {
        params.ordering = getSortParam({ field, direction });
    }
    return await axios.get(`/projects/${projectId}/characters`, { params });
};

// retrieve a list of documents by project
// TODO: Is this the right place for this, or would it be better to filter docs by
// project pk?
export const retrieveProjectDocuments = async ({
    projectId,
    field,
    direction,
}) => {
    let params = {};
    if (field && direction) {
        params.ordering = getSortParam({ field, direction });
    }
    return await axios.get(`/projects/${projectId}/documents`, { params });
};
