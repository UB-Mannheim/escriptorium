import { ManyTags } from "../Tags.stories";

/* eslint-disable max-len */

// mock models
export const models = [
    {
        pk: 1,
        name: "arabPersPrBigMixed_best",
        file:
            "https://github.com/OpenITI/ocr_with_kraken_public/raw/main/models/arabPersPrBigMixed_best%20(1).mlmodel",
        file_size: 20036695,
        job: "Recognize",
        training: false,
        accuracy_percent: 95.25439143180847,
        rights: "owner",
        script: "Arabic",
        parent: "ap1ksplit21-ft-best",
    },
    {
        pk: 2,
        name: "ap1ksplit21-ft-best",
        file:
            "https://github.com/OpenITI/ocr_with_kraken_public/raw/main/models/arabPersPrBigMixed_best%20(1).mlmodel",
        file_size: 20036695,
        job: "Recognize",
        training: false,
        accuracy_percent: 95.25439143180847,
        rights: "owner",
    },
    {
        pk: 9,
        name: "arabPersPrBigMixed_best (1)",
        file:
            "https://github.com/OpenITI/ocr_with_kraken_public/raw/main/models/arabPersPrBigMixed_best%20(1).mlmodel",
        file_size: 5052823,
        job: "Segment",
        training: false,
        accuracy_percent: 63.7286312309023,
        rights: "owner",
    },
];

// mock ontologies for all stories with ontology
export const blockTypes = [
    { pk: 1, name: "Main", count: 22 },
    { pk: 2, name: "Commentary", count: 3 },
    { pk: 3, name: "Header", count: 1 },
    { pk: 4, name: "Illustration", count: 4 },
    { pk: 5, name: "Footnote", count: 4 },
];
export const blockTypesRandomized = [
    ...blockTypes.map((b) => ({
        ...b,
        count: Math.ceil(Math.random() * 30),
    })),
    { pk: 0, name: "Extra type", count: 33 },
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

export const charactersRandomized = characters.map((c) => ({
    ...c,
    frequency: Math.ceil(Math.random() * 2000),
}));

// mock groups for all stories with groups
export const groups = [
    { pk: 1, name: "Group Name 1" },
    { pk: 2, name: "Group Name 2" },
    { pk: 3, name: "Group Name 3" },
];

// mock users for all stories with users
export const users = [
    { pk: 1, first_name: "Elwin", last_name: "Abbott", username: "eabbott" },
    { pk: 2, first_name: "Marcos", last_name: "Prosacco", username: "mpro" },
    { pk: 3, first_name: "Emmy", last_name: "Leuschke", username: "eleu" },
    {
        pk: 4,
        first_name: "Salvatore",
        last_name: "Spencer",
        username: "salspen",
    },
    { pk: 5, first_name: "Nathanial", last_name: "Olson", username: "natols" },
    { pk: 6, username: "someuser" },
];

export const transcriptions = [
    {
        pk: 1,
        name: "manual",
        archived: false,
        avg_confidence: null,
        lines_count: 2000,
    },
    {
        pk: 2,
        name: "Example transcription level",
        archived: false,
        avg_confidence: 0.8235823,
        lines_count: 20,
    },
];
