import { thumbnail } from "../../../src/util/dropzone";

// a dropzone preview element, as its previewTemplate builds it
const makeFile = (name = "page.jpg") => {
    const previewElement = document.createElement("div");
    previewElement.classList.add("dz-file-preview");
    const img = document.createElement("img");
    img.setAttribute("data-dz-thumbnail", "");
    previewElement.appendChild(img);
    return { name, previewElement };
};

const thumbnailImg = (file) =>
    file.previewElement.querySelector("[data-dz-thumbnail]");

describe("dropzone thumbnail handler", () => {
    beforeEach(() => {
        jest.useFakeTimers();
    });

    afterEach(() => {
        jest.useRealTimers();
    });

    describe("with a real data URL", () => {
        const dataUrl = "data:image/png;base64,iVBORw0KGgo=";

        it("sets the preview src and alt", () => {
            const file = makeFile();

            thumbnail(file, dataUrl);

            expect(thumbnailImg(file).getAttribute("src")).toBe(dataUrl);
            expect(thumbnailImg(file).alt).toBe("page.jpg");
        });

        it("swaps the preview classes the way dropzone's css expects", () => {
            const file = makeFile();

            thumbnail(file, dataUrl);
            expect(file.previewElement.classList.contains("dz-file-preview")).toBe(
                false,
            );
            // dropzone defers this by a tick
            expect(file.previewElement.classList.contains("dz-image-preview")).toBe(
                false,
            );

            jest.runAllTimers();
            expect(file.previewElement.classList.contains("dz-image-preview")).toBe(
                true,
            );
        });

        it("handles a preview with several thumbnail elements", () => {
            const file = makeFile();
            const second = document.createElement("img");
            second.setAttribute("data-dz-thumbnail", "");
            file.previewElement.appendChild(second);

            thumbnail(file, dataUrl);

            file.previewElement
                .querySelectorAll("[data-dz-thumbnail]")
                .forEach((img) => expect(img.getAttribute("src")).toBe(dataUrl));
        });
    });

    describe("when the browser could not decode the file", () => {
        it("leaves the src alone rather than requesting [object Event]", () => {
            // dropzone does `img.onerror = callback`, so the callback that normally
            // receives a data URL receives the DOM Event instead
            const file = makeFile("scan.tiff");

            thumbnail(file, new Event("error"));

            expect(thumbnailImg(file).getAttribute("src")).toBeNull();
            // the placeholder styling stays
            expect(file.previewElement.classList.contains("dz-file-preview")).toBe(
                true,
            );
        });

        it("is the string that used to end up in the URL", () => {
            // pins the reported symptom: GET /document/115/images/[object Event]
            expect(String(new Event("error"))).toBe("[object Event]");
        });

        it.each([
            ["undefined", undefined],
            ["null", null],
            ["a number", 42],
            ["an object", {}],
        ])("ignores %s", (_label, value) => {
            const file = makeFile("scan.tiff");

            thumbnail(file, value);

            expect(thumbnailImg(file).getAttribute("src")).toBeNull();
        });
    });

    it("does nothing when the file has no preview element", () => {
        // previews are optional, e.g. previewsContainer: false
        expect(() =>
            thumbnail({ name: "page.jpg" }, "data:image/png;base64,x"),
        ).not.toThrow();
    });
});
