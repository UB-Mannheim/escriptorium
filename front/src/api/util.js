// convenience object mapping frontend labels to ontology model names in API
export const ontologyMap = {
    regions: "block",
    lines: "line",
    text: "annotations",
    images: "part",
};

// construct the URL param for ordering/sort
export const getSortParam = ({ field, direction }) => {
    let ordering = field;
    if (direction == -1) {
        ordering = `-${field}`;
    }
    return ordering;
};

// construct URL params for filters
export const getFilterParams = ({ filters }) => {
    const params = {};
    filters.forEach((filter) => {
        params[filter.type] = filter.value;
        if (filter.operator) params[`${filter.type}_op`] = filter.operator;
    });
    return params;
};
