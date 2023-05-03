import axios from "axios";
import { getFilterParams, getSortParam } from "./util";

// retrieve the full list of documents, with filters/sort
export const retrieveDocumentsList = async ({
    projectId,
    field,
    direction,
    filters,
}) => {
    let params = {};
    if (projectId) {
        params.project = projectId;
    }
    if (field && direction) {
        params.ordering = getSortParam({ field, direction });
    }
    if (filters) {
        params = { ...params, ...getFilterParams({ filters }) };
    }
    return await axios.get("/documents", { params });
};

// create a new document
export const createDocument = async ({
    name,
    project,
    mainScript,
    readDirection,
    linePosition,
    tags,
}) =>
    await axios.post("/documents", {
        params: {
            name,
            project,
            main_script: mainScript,
            read_direction: readDirection,
            line_offset: linePosition,
            tags,
        },
    });

export const deleteDocument = async ({ documentId }) =>
    await axios.delete(`/documents/${documentId}`);
