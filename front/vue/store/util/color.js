import ColorClassifier from "color-classifier";

export const tagVariants = [
    "#c6c4c4",
    "#adffd9",
    "#adfeff",
    "#99e6ff",
    "#88c9f2",
    "#99aff2",
    "#b3b3e6",
    "#c195db",
    "#da9ecf",
    "#f2a7c3",
    "#dc8f8d",
    "#ff9a6f",
    "#fcb55f",
    "#f7ed78",
    "#cbe364",
    "#a9d69a",
    "#006644",
    "#006666",
    "#006699",
    "#0074de",
    "#3864e5",
    "#5056ce",
    "#5d36b4",
    "#a126a0",
    "#d61c71",
    "#ed0020",
    "#ff621f",
    "#fba841",
    "#e7d50d",
    "#979f34",
    "#41742f",
];

/**
 * Map a hex color to its perceptually closest matching tag variant in the above list,
 */
export const tagColorToVariant = (color) => {
    const colorClassifier = new ColorClassifier(tagVariants);

    if (tagVariants.includes(color)) {
        // it's in the list; use index + 1 (variants are 1-indexed)
        return tagVariants.indexOf(color) + 1;
    } else {
        // it's not in the list; use index + 1 of perceptually closest variant
        const variant = colorClassifier.classify(color, "hex");
        return tagVariants.indexOf(variant) + 1;
    }
};
