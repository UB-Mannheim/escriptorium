// utility function for sorting lists in mock API responses
export const sorted = (items, { ordering }) => {
    const alphabeticSort = (key) => (a, b) => {
        return a[key].toString().localeCompare(b[key].toString());
    };
    const numericSort = (key) => (a, b) => {
        return a[key] - b[key];
    };
    if (!ordering) {
        return [...items].sort(numericSort("id"));
    } else {
        // handle ordering param ("sortfield" = asc, "-sortfield" = desc)
        let sorted = [...items];
        const split = ordering.split("-");
        const sort = split.length == 1 ? split[0] : split[1];
        if (ordering.includes("count")) {
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
