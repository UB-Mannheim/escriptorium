import { guardThumbnail } from "../../../src/util/dropzone";

describe("guardThumbnail", () => {
    let defaultThumbnail, thumbnail;

    beforeEach(() => {
        defaultThumbnail = jest.fn();
        thumbnail = guardThumbnail(defaultThumbnail);
    });

    it("passes a real data URL through to the default handler", () => {
        const file = { name: "page.jpg" };
        const dataUrl = "data:image/png;base64,iVBORw0KGgo=";

        thumbnail.call({ instance: true }, file, dataUrl);

        expect(defaultThumbnail).toHaveBeenCalledWith(file, dataUrl);
    });

    it("keeps the dropzone instance as `this`", () => {
        // the default handler reads file.previewElement off the instance context
        const instance = { marker: 1 };
        defaultThumbnail = jest.fn(function () {
            expect(this).toBe(instance);
        });

        guardThumbnail(defaultThumbnail).call(instance, {}, "data:image/png;base64,x");

        expect(defaultThumbnail).toHaveBeenCalled();
    });

    it("ignores the error Event dropzone sends when a file can't be decoded", () => {
        // dropzone does `img.onerror = callback`, so the callback that normally
        // receives a data URL receives the DOM Event instead. Assigning that to
        // img.src requests "[object Event]" relative to the current page.
        const event = new Event("error");

        thumbnail.call({}, { name: "scan.tiff" }, event);

        expect(defaultThumbnail).not.toHaveBeenCalled();
    });

    it("would otherwise have produced an [object Event] src", () => {
        // guards the regression itself: this is the string that ended up in the URL
        expect(String(new Event("error"))).toBe("[object Event]");
    });

    it.each([
        ["undefined", undefined],
        ["null", null],
        ["a number", 42],
        ["an object", {}],
    ])("ignores %s", (_label, value) => {
        thumbnail.call({}, { name: "scan.tiff" }, value);

        expect(defaultThumbnail).not.toHaveBeenCalled();
    });
});
