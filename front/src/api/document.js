import axios from "axios";
import { getFilterParams, getSortParam, ontologyMap } from "./util";

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
    return await axios.get("/documents/", { params });
};

// retrieve single document by ID
export const retrieveDocument = async (documentId) =>
    await axios.get(`/documents/${documentId}/`);

// retrieve types list for a document
export const retrieveDocumentStats = async ({
    documentId,
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
        `/documents/${documentId}/stats/`,
        { params },
    );
};

// retrieve default types list by category (regions, lines, parts)
export const retrieveDefaultOntology = async (category) =>
    await axios.get(`/${ontologyMap[category]}/`);

// create, update, destroy ontology types
export const createType = async (category, data) =>
    await axios.post(`/${ontologyMap[category]}/`, data);

export const createAnnotationType = async ({ documentId, target, data }) =>
    await axios.post(
        `/documents/${documentId}/taxonomies/annotations/?target=${target}`,
        data,
    );

export const updateType = async (category, { typePk, ...data }) =>
    await axios.patch(`/${ontologyMap[category]}/${typePk}/`, data);

export const updateAnnotationType = async ({ documentId, typePk, data }) =>
    await axios.patch(
        `/documents/${documentId}/taxonomies/annotations/${typePk}/`,
        data,
    );

export const deleteType = async (category, { typePk, ...data }) =>
    await axios.delete(`/${ontologyMap[category]}/${typePk}/`, data);

export const deleteAnnotationType = async ({ documentId, typePk }) =>
    await axios.delete(
        `/documents/${documentId}/taxonomies/annotations/${typePk}/`,
    );

export const updateDocumentOntology = async (documentId, data) =>
    await axios.patch(`/documents/${documentId}/modify_ontology/`, data);

// retrieve the taxonomies for annotation components
export const retrieveComponentTaxonomies = async (documentId) =>
    await axios.get(
        `/documents/${documentId}/taxonomies/components/?paginate_by=50`,
    );

// retrieve the taxonomies for annotation components
export const createComponentTaxonomy = async ({
    documentId,
    name,
    allowedValues,
}) =>
    await axios.post(`/documents/${documentId}/taxonomies/components/`, {
        name,
        allowed_values: allowedValues,
    });

// update an annotation component
export const updateComponentTaxonomy = async ({
    documentId,
    name,
    allowedValues,
    pk,
}) =>
    await axios.patch(`/documents/${documentId}/taxonomies/components/${pk}/`, {
        name,
        allowed_values: allowedValues,
    });

// delete an annotation component
export const deleteComponentTaxonomy = async ({ documentId, pk }) =>
    await axios.delete(`/documents/${documentId}/taxonomies/components/${pk}/`);

// retrieve characters, sorted by character or frequency, for a specific transcription on a document
export const retrieveTranscriptionStats = async ({
    documentId,
    transcriptionId,
    field,
    direction,
}) => {
    let ordering = "-frequency";
    if (field && direction) {
        ordering = getSortParam({ field, direction });
    }
    return await axios.get(
        // eslint-disable-next-line max-len
        `/documents/${documentId}/transcriptions/${transcriptionId}/stats/?ordering=${ordering}`,
    );
};

// retrieve the total number of characters in a specific transcription level on a document
export const retrieveTranscriptionCharCount = async ({
    documentId,
    transcriptionId,
}) => {
    return await axios.get(
        `/documents/${documentId}/transcriptions/${transcriptionId}/character_count/`,
    );
};

export const updateTranscription = async ({
    documentId,
    transcriptionId,
    name,
    comments,
}) =>
    await axios.put(
        `/documents/${documentId}/transcriptions/${transcriptionId}/`,
        { name, comments },
    );

// retrieve document parts
export const retrieveDocumentParts = async ({
    documentId,
    field,
    direction,
    pageSize,
}) => {
    let params = {};
    if (field && direction) {
        params.ordering = getSortParam({ field, direction });
    }
    if (pageSize) {
        params.paginate_by = pageSize;
    }
    return await axios.get(`/documents/${documentId}/parts/`, { params });
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
    await axios.post("/documents/", {
        name,
        project,
        main_script: mainScript,
        read_direction: readDirection,
        line_offset: linePosition,
        tags,
    });

// delete a document
export const deleteDocument = async ({ documentId }) =>
    await axios.delete(`/documents/${documentId}/`);

// edit a document
export const editDocument = async (
    documentId,
    { name, project, mainScript, readDirection, linePosition, tags },
) =>
    await axios.put(`/documents/${documentId}/`, {
        name,
        project,
        main_script: mainScript,
        read_direction: readDirection,
        line_offset: linePosition,
        tags,
    });

// retrieve document metadata
export const retrieveDocumentMetadata = async (documentId) =>
    await axios.get(`/documents/${documentId}/metadata/`);

// create document metadata
export const createDocumentMetadata = async ({ documentId, metadatum }) =>
    await axios.post(`/documents/${documentId}/metadata/`, {
        ...metadatum,
    });

// update document metadata
export const updateDocumentMetadata = async ({ documentId, metadatum }) =>
    await axios.put(`/documents/${documentId}/metadata/${metadatum.pk}/`, {
        ...metadatum,
    });

// delete document metadata
export const deleteDocumentMetadata = async ({ documentId, metadatumId }) =>
    await axios.delete(`/documents/${documentId}/metadata/${metadatumId}/`);

// retrieve document models
export const retrieveDocumentModels = async (documentId) =>
    await axios.get("/models/", {
        params: {
            documents: documentId,
        },
    });

const jobTypeIds = {
    segment: 1,
    recognize: 2,
};

// retrieve all models (by job type)
export const retrieveModels = async (jobType) =>
    await axios.get("/models/", { params: { job: jobTypeIds[jobType] } });

// share this document with a group or user
export const shareDocument = async ({ documentId, group, user }) =>
    await axios.post(`/documents/${documentId}/share/`, {
        group,
        user,
    });

// queue the segmentation task for this document
export const segmentDocument = async ({
    documentId,
    override,
    model,
    steps,
    parts,
}) => {
    const params = { steps, parts };
    if (override) {
        params["override"] = override;
    }
    if (model) {
        params["model"] = model;
    }
    await axios.post(`/documents/${documentId}/segment/`, params);
};

// queue the transcription task for this document
export const transcribeDocument = async ({
    documentId,
    model,
    transcription,
    parts,
}) =>
    await axios.post(`/documents/${documentId}/transcribe/`, {
        model,
        transcription,
        parts,
    });

// retrieve textual witnesses for use in alignment
export const retrieveTextualWitnesses = async () =>
    await axios.get("/textual-witnesses/");

// queue the alignment task for this document
export const alignDocument = async ({
    documentId,
    beamSize,
    existingWitness,
    fullDoc,
    gap,
    layerName,
    maxOffset,
    merge,
    ngram,
    regionTypes,
    threshold,
    transcription,
    witnessFile,
    parts,
}) => {
    // need to use FormData to handle witness file upload
    const formData = new FormData();
    if (beamSize) formData.append("beam_size", beamSize);
    if (existingWitness) formData.append("existing_witness", existingWitness);
    formData.append("full_doc", fullDoc);
    formData.append("gap", gap);
    formData.append("layer_name", layerName);
    if (maxOffset) formData.append("max_offset", maxOffset);
    formData.append("merge", merge);
    formData.append("n_gram", ngram);
    if (regionTypes?.length) {
        regionTypes.forEach((type) => formData.append("region_types", type));
    }
    formData.append("threshold", threshold);
    formData.append("transcription", transcription);
    if (witnessFile) formData.append("witness_file", witnessFile);
    if (parts?.length) {
        parts.forEach((part) => formData.append("parts", part));
    }
    const headers = { "Content-Type": "multipart/form-data" };
    return await axios.post(`/documents/${documentId}/align/`, formData, {
        headers,
    });
};

// queue the export task for this document
export const exportDocument = async ({
    documentId,
    fileFormat,
    includeImages,
    regionTypes,
    transcription,
    parts,
}) =>
    await axios.post(`/documents/${documentId}/export/`, {
        region_types: regionTypes,
        file_format: fileFormat,
        include_images: includeImages,
        transcription,
        parts,
    });

// queue the import task for this document
export const queueImport = async ({ documentId, params }) => {
    if (params["upload_file"]) {
        // need to use FormData to handle file upload
        const formData = new FormData();
        Object.keys(params).forEach((key) => {
            formData.append(key, params[key]);
        });
        const headers = { "Content-Type": "multipart/form-data" };
        return await axios.post(`/documents/${documentId}/import/`, formData, {
            headers,
        });
    }
    return await axios.post(`/documents/${documentId}/import/`, params);
};

// retrieve latest tasks for a document
export const retrieveDocumentTasks = async ({ documentId }) =>
    await axios.get("/tasks/", {
        params: {
            document: documentId,
        },
    });

// cancel a task on a document by pk
export const cancelTask = async ({ documentId, taskReportId }) =>
    await axios.post(`/documents/${documentId}/cancel_tasks/`, {
        task_report: taskReportId,
    });

// create a new transcription layer
export const createTranscriptionLayer = async ({ documentId, layerName }) =>
    await axios.post(`/documents/${documentId}/transcriptions/`, {
        name: layerName,
    });

// delete a part (image) on a document
export const deleteDocumentPart = async ({ documentId, partPk }) =>
    await axios.delete(`/documents/${documentId}/parts/${partPk}/`);

export const trainRecognizerModel = async ({
    documentId,
    model,
    modelName,
    override,
    parts,
    transcription,
}) => {
    const params = {
        override,
        parts,
        transcription,
        model_name: modelName,
    };
    if (model) {
        params.model = model;
    }
    if (modelName) {
        params.model_name = modelName;
    }
    return await axios.post(`/documents/${documentId}/train/`, params);
};

export const trainSegmenterModel = async ({
    documentId,
    model,
    modelName,
    override,
    parts,
}) => {
    const params = {
        override,
        parts,
    };
    if (model) {
        params.model = model;
    }
    if (modelName) {
        params.model_name = modelName;
    }
    return await axios.post(`/documents/${documentId}/segtrain/`, params);
};
