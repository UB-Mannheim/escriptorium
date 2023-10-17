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
};

// tags filter utility function
export const filteredByTag = (items, tags) => {
    // "or" operator will be formatted like "2|3|none", so split by |
    let tagArray =
        tags && tags.includes("|") ? tags.split("|") : tags.split(",");
    // convert all pks to strings for comparison with api response
    tagArray = tagArray ? tagArray.map((t) => t.toString()) : [];
    if (tags && tagArray) {
        return items.filter((item) => {
            if (
                (!Array.isArray(tags) || tags.length === 1) &&
                tagArray.includes("none") &&
                !item.tags.length
            ) {
                // "none" selected and either this is "or" operator, or it's "and" with one entry
                return true;
            } else if (!Array.isArray(tags)) {
                // "or" operator
                return item.tags?.some((itemTag) =>
                    tagArray.includes(itemTag.pk.toString()),
                );
            } else {
                // "and" operator
                return tagArray.every((tag) =>
                    item.tags?.some((itemTag) => itemTag.pk.toString() === tag),
                );
            }
        });
    }
    return items;
};
