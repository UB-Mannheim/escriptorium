// sort utility functions
const alphabeticSort = (key) => (a, b) => {
    return a[key].toString().localeCompare(b[key].toString());
};
const numericSort = (key) => (a, b) => {
    return a[key] - b[key];
};

// utility function for sorting lists in mock API responses
export const sorted = (items, { ordering }) => {
    if (!ordering) {
        return [...items].sort(numericSort("id"));
    } else {
        // handle ordering param ("sortfield" = asc, "-sortfield" = desc)
        let sorted = [...items];
        const split = ordering.split("-");
        const sort = split.length == 1 ? split[0] : split[1];
        if (ordering.includes("count") || ordering.includes("-frequency")) {
            sorted.sort(numericSort(sort));
        } else {
            sorted.sort(alphabeticSort(sort));
        }
        if (split.length == 2) {
            sorted.reverse();
        }
        return sorted;
    }
};

// utility function to sort in place when we aren't using API
export const onSort = (items, { field, direction }) => {
    if (direction === 0) {
        items.sort(numericSort("pk"));
    } else if (field.includes("count")) {
        items.sort(numericSort(field));
    } else {
        items.sort(alphabeticSort(field));
    }
    if (direction === -1) {
        items.reverse();
    }
}

// mock ontologies for all stories with ontology
export const blockTypes = [
    { pk: 1, name: "Main", count: 22 },
    { pk: 2, name: "Commentary", count: 3 },
    { pk: 3, name: "Header", count: 1 },
    { pk: 4, name: "Illustration", count: 4 },
    { pk: 5, name: "Footnote", count: 4 },
];
export const lineTypes = [
    { pk: 1, name: "Correction", count: 13 },
    { pk: 2, name: "Main", count: 101 },
];
export const annotationTypes = [
    { pk: 1, name: "Quote", count: 4 },
    { pk: 2, name: "Translation", count: 11 },
];
export const partTypes = [
    { pk: 1, name: "Cover", count: 4 },
    { pk: 2, name: "Page", count: 100 },
];
