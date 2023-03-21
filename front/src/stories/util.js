import { ManyTags } from "./Tags.stories";

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
export const filteredByTag = (items, tags, operator, withoutTag) => {
    if (tags) {
        return items.filter((item) => {
            if (withoutTag && !item.tags.length) {
                return true;
            }
            if (operator === "or") {
                return item.tags?.some((itemTag) =>
                    tags.includes(itemTag.pk),
                );
            } else {
                return tags.every((tag) =>
                    item.tags?.some((itemTag) => itemTag.pk === tag),
                );
            }
        });
    }
    return items;
};

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

// mock tags for all stories with tags
export const tags = [
    ...ManyTags.args.tags,
    {
        pk: 7,
        name: "Tag",
        variant: 4,
        color: "#fcb55f",
    },
    {
        pk: 8,
        name: "Tag tag",
        variant: 7,
        color: "#80c6ba",
    },
    {
        pk: 9,
        name: "Other tag",
        variant: 8,
        color: "#88c9f2",
    },
    {
        pk: 10,
        name: "A tag",
        variant: 6,
        color: "#cbe364",
    },
];

// mock characters for all stories with characters
export const characters = [
    { char: " ", frequency: 2285 },
    { char: "ئ", frequency: 58 },
    { char: "ع", frequency: 1008 },
    { char: "و", frequency: 1858 },
    { char: "ك", frequency: 222 },
    { char: "0", frequency: 3 },
    { char: "1", frequency: 2 },
    { char: "2", frequency: 10 },
    { char: "a", frequency: 15 },
    { char: "b", frequency: 85 },
    { char: "c", frequency: 3 },
    { char: "d", frequency: 6 },
    { char: "e", frequency: 12 },
    { char: "f", frequency: 68 },
    { char: "g", frequency: 2 },
    { char: "h", frequency: 44 },
    { char: "i", frequency: 5 },
    { char: "j", frequency: 7 },
    { char: "k", frequency: 8 },
    { char: "l", frequency: 2 },
    { char: "m", frequency: 89 },
    { char: "n", frequency: 1 },
    { char: "o", frequency: 11 },
    { char: "p", frequency: 22 },
    { char: "q", frequency: 33 },
    { char: "r", frequency: 41 },
    { char: "s", frequency: 64 },
    { char: "t", frequency: 86 },
    { char: "u", frequency: 38 },
    { char: "v", frequency: 86 },
    { char: "w", frequency: 66 },
    { char: "x", frequency: 58 },
    { char: "y", frequency: 65 },
    { char: "z", frequency: 77 },
    { char: "{", frequency: 22 },
    { char: "}", frequency: 1 },
    { char: "ؤ", frequency: 24 },
    { char: "‐", frequency: 56 },
    { char: "'", frequency: 2 },
    { char: ".", frequency: 5 },
    { char: ",", frequency: 33 },
    { char: "/", frequency: 27 },
    { char: "(", frequency: 8 },
    { char: ")", frequency: 8 },
];

// mock groups for all stories with groups
export const groups = [
    { pk: 1, name: "Group Name 1" },
    { pk: 2, name: "Group Name 2" },
    { pk: 3, name: "Group Name 3" },
]

// mock users for all stories with users
export const users = [
    { pk: 1, first_name: "Elwin", last_name: "Abbott", username: "eabbott" },
    { pk: 2, first_name: "Marcos", last_name: "Prosacco", username: "mpro" },
    { pk: 3, first_name: "Emmy", last_name: "Leuschke", username: "eleu" },
    { pk: 4, first_name: "Salvatore", last_name: "Spencer", username: "salspen" },
    { pk: 5, first_name: "Nathanial", last_name: "Olson", username: "natols" },
    { pk: 6, username: "someuser" },
]
