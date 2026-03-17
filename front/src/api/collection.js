import axios from "axios";

// fetch all collections (paginated)
export const retrieveCollections = async () =>
    await axios.get("/collections/");

// fetch a single collection by ID
export const retrieveCollection = async (collectionId) =>
    await axios.get(`/collections/${collectionId}/`);

// fetch all collection items (paginated)
export const retrieveCollectionItems = async (collectionId) =>
    await axios.get(`/collections/${collectionId}/items/`);

// create a new collection
export const createCollection = async (payload) =>
    await axios.post("/collections/", payload);

// update an existing collection
export const updateCollection = async (collectionId, payload) =>
    await axios.put(`/collections/${collectionId}/`, payload);

// fetch task groups associated with a collection
export const retrieveCollectionTasks = async (collectionId) =>
    await axios.get(`/taskgroup/?collection=${collectionId}`);

// train a recognition model on a collection
export const trainCollectionRecognizer = async (collectionId, payload) =>
    await axios.post(`/collections/${collectionId}/train_recognizer/`, payload);

// train a segmentation model on a collection
export const trainCollectionSegmenter = async (collectionId, payload) =>
    await axios.post(`/collections/${collectionId}/train_segmenter/`, payload);
