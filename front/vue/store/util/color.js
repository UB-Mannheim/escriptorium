import ColorClassifier from "color-classifier";

const tagVariants = [
    "#e0726e",
    "#f78d8d",
    "#ff9a6f",
    "#fcb55f",
    "#f2cd5c",
    "#cbe364",
    "#80c6ba",
    "#88c9f2",
    "#99aff2",
    "#c195db",
    "#f2a7c3",
    "#c6c4c4",
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
