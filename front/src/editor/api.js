import axios from "axios";

axios.defaults.baseURL = "/api";
axios.defaults.xsrfCookieName = "csrftoken";
axios.defaults.xsrfHeaderName = "X-CSRFToken";
axios.defaults.withCredentials = true;

export const retrieveDocument = async (document_id) =>
    await axios.get(`/documents/${document_id}/`);

export const retrievePage = async (document_id, part_id, transcription, page) =>
    await axios.get(
        `/documents/${document_id}/parts/${part_id}/transcriptions/?transcription=${transcription}&page=${page}`,
    );

export const retrieveAnnotationTaxonomies = async (document_id, target, page) =>
    await axios.get(
        `/documents/${document_id}/taxonomies/annotations/?target=${target}&page=${page}&paginate_by=50`,
    );

export const retrieveImageAnnotations = async (document_id, part_id, page) =>
    await axios.get(
        `/documents/${document_id}/parts/${part_id}/annotations/image/?page=${page}`,
    );

export const retrieveTextAnnotations = async (
    document_id,
    part_id,
    transcription_id,
    page,
) =>
    await axios.get(
        `/documents/${document_id}/parts/${part_id}/annotations/text/?transcription=${transcription_id}&page=${page}`,
    );

export const createContent = async (document_id, part_id, data) =>
    await axios.post(
        `/documents/${document_id}/parts/${part_id}/transcriptions/`,
        data,
    );

export const updateContent = async (document_id, part_id, id, data) =>
    await axios.put(
        `/documents/${document_id}/parts/${part_id}/transcriptions/${id}/`,
        data,
    );

export const bulkCreateLines = async (document_id, part_id, data) =>
    await axios.post(
        `/documents/${document_id}/parts/${part_id}/lines/bulk_create/`,
        data,
    );

export const bulkUpdateLines = async (document_id, part_id, data) =>
    await axios.put(
        `/documents/${document_id}/parts/${part_id}/lines/bulk_update/`,
        data,
    );

export const bulkDeleteLines = async (document_id, part_id, data) =>
    await axios.post(
        `/documents/${document_id}/parts/${part_id}/lines/bulk_delete/`,
        data,
    );

export const mergeLines = async (document_id, part_id, data) =>
    await axios.post(
        `/documents/${document_id}/parts/${part_id}/lines/merge/`,
        data,
    );

export const recalculateMasks = async (document_id, part_id, data, params) =>
    await axios.post(
        `/documents/${document_id}/parts/${part_id}/reset_masks/`,
        data,
        { params: params },
    );

export const recalculateOrdering = async (document_id, part_id, data) =>
    await axios.post(
        `/documents/${document_id}/parts/${part_id}/recalculate_ordering/`,
        data,
    );

export const createRegion = async (document_id, part_id, data) =>
    await axios.post(
        `/documents/${document_id}/parts/${part_id}/blocks/`,
        data,
    );

export const updateRegion = async (document_id, part_id, id, data) =>
    await axios.put(
        `/documents/${document_id}/parts/${part_id}/blocks/${id}/`,
        data,
    );

export const deleteRegion = async (document_id, part_id, id) =>
    await axios.delete(
        `/documents/${document_id}/parts/${part_id}/blocks/${id}/`,
    );

export const archiveTranscription = async (document_id, id) =>
    await axios.delete(`/documents/${document_id}/transcriptions/${id}/`);

export const bulkCreateLineTranscriptions = async (
    document_id,
    part_id,
    data,
) =>
    await axios.post(
        `/documents/${document_id}/parts/${part_id}/transcriptions/bulk_create/`,
        data,
    );

export const bulkUpdateLineTranscriptions = async (
    document_id,
    part_id,
    data,
) =>
    await axios.put(
        `/documents/${document_id}/parts/${part_id}/transcriptions/bulk_update/`,
        data,
    );

export const moveLines = async (document_id, part_id, data) =>
    await axios.post(
        `/documents/${document_id}/parts/${part_id}/lines/move/`,
        data,
    );

export const createImageAnnotation = async (document_id, part_id, data) =>
    await axios.post(
        `documents/${document_id}/parts/${part_id}/annotations/image/`,
        data,
    );

export const createTextAnnotation = async (document_id, part_id, data) =>
    await axios.post(
        `documents/${document_id}/parts/${part_id}/annotations/text/`,
        data,
    );

export const updateImageAnnotation = async (document_id, part_id, id, data) =>
    await axios.patch(
        `/documents/${document_id}/parts/${part_id}/annotations/image/${id}/`,
        data,
    );

export const updateTextAnnotation = async (document_id, part_id, id, data) =>
    await axios.patch(
        `/documents/${document_id}/parts/${part_id}/annotations/text/${id}/`,
        data,
    );

export const deleteImageAnnotation = async (document_id, part_id, id) =>
    await axios.delete(
        `/documents/${document_id}/parts/${part_id}/annotations/image/${id}/`,
    );

export const deleteTextAnnotation = async (document_id, part_id, id) =>
    await axios.delete(
        `/documents/${document_id}/parts/${part_id}/annotations/text/${id}/`,
    );

export const createProjectTag = async (project_id, data) =>
    await axios.post(`/projects/${project_id}/tags/`, data);

export const updateDocument = async (document_id, data) =>
    await axios.patch(`/documents/${document_id}/`, data);

export const deletetag = async (project_id, tag_id) =>
    await axios.delete(`/projects/${project_id}/tags/${tag_id}/`);

export const updatetag = async (project_id, tag_id, data) =>
    await axios.put(`/projects/${project_id}/tags/${tag_id}/`, data);
