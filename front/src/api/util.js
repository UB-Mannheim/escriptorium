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
        if (filter.operator === "or" && Array.isArray(filter.value)) {
            // "or" should be constructed as "?tags=1|2|none" for api
            params[filter.type] = filter.value.join("|");
        } else {
            // "and" should be constructed as "?tags=1&tags=2" for api, so pass array
            params[filter.type] = filter.value;
        }
    });
    return params;
};
