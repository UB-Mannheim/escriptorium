// convenience object mapping frontend labels to ontology model names in API
export const ontologyMap = {
    regions: "types/block",
    lines: "types/line",
    parts: "types/part",
    text: "taxonomies/annotations",
    image: "taxonomies/annotations",
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
        } else if (Array.isArray(filter.value)) {
            // "and" should be constructed as "?tags=1,2" for api, so pass array
            params[filter.type] = filter.value.join(",");
        } else {
            params[filter.type] = filter.value;
        }
    });
    return params;
};
