// Utility to store the initial state for each form, so that forms can easily be cleared by key/name

export default {
    editDocument: {
        linePosition: "",
        mainScript: "",
        metadata: [],
        name: "",
        readDirection: "",
        tags: [],
        tagName: "",
    },
    editProject: {
        guidelines: "",
        name: "",
        tags: [],
        tagName: "",
    },
    segment: {
        model: "",
        overwrite: false,
        include: [],
        textDirection: "",
    },
    share: {
        group: "",
        user: "",
    },
};
