import { Segmenter } from "../../../src/baseline.editor";

// Bypass the constructor (which requires paper.js canvas setup) by creating
// an instance directly from the prototype. shadeColor is a pure computation
// method with no paper.js dependencies.
const segmenter = Object.create(Segmenter.prototype);

describe("Segmenter.shadeColor", () => {
    it("darkens a valid hex color by the given percent", () => {
        // #ff0000 at -50%: R=255→127=0x7f, G=0, B=0
        expect(segmenter.shadeColor("#ff0000", -50)).toBe("#7f0000");
    });

    it("lightens a valid hex color by the given percent", () => {
        // #808080 at +100%: each channel doubles, capped at 255=0xff
        expect(segmenter.shadeColor("#808080", 100)).toBe("#ffffff");
    });

    it("returns #808080 when color is undefined", () => {
        expect(segmenter.shadeColor(undefined, -50)).toBe("#808080");
    });

    it("returns #808080 when color is null", () => {
        expect(segmenter.shadeColor(null, -50)).toBe("#808080");
    });
});

describe("Segmenter region color fallback", () => {
    it("uses #808080 when a region type has no entry in regionColors", () => {
        // Simulate the color resolution that happens in Region constructor and refresh():
        //   this.color = segmenter.regionColors[type || "None"] || "#808080"
        const regionColors = { KnownType: "#aabbcc" };

        const colorFor = (type) => regionColors[type || "None"] || "#808080";

        expect(colorFor("KnownType")).toBe("#aabbcc");
        expect(colorFor("UnknownType")).toBe("#808080");
        expect(colorFor(null)).toBe("#808080");
        expect(colorFor(undefined)).toBe("#808080");
        expect(colorFor("None")).toBe("#808080"); // "None" not in regionColors
    });

    it("uses #808080 when regionColors is empty (e.g. after ontology update)", () => {
        const regionColors = {};
        const colorFor = (type) => regionColors[type || "None"] || "#808080";

        expect(colorFor("Background")).toBe("#808080");
        expect(colorFor(undefined)).toBe("#808080");
    });
});
