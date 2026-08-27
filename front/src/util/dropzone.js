/**
 * Replacement for dropzone's default `thumbnail` option.
 *
 * Dropzone builds its preview thumbnails by loading the dropped file into an
 * <img>, and reuses a single callback for both outcomes (dropzone.js):
 *
 *     if (callback != null) { img.onerror = callback; }
 *     return img.src = file.dataURL;
 *
 * On success the callback receives a data URL; on failure it receives the DOM
 * error Event. Nothing distinguishes them, so the default handler assigns the
 * event to img.src. That stringifies to "[object Event]", which the browser
 * resolves against the current page, producing a 404 like
 *     GET /document/115/images/[object Event]
 *
 * It happens for every file the browser cannot decode -- always for TIFF, which
 * no browser renders in an <img>, and also for corrupt or CMYK images. The
 * upload itself is unaffected: dropzone queues thumbnails and uploads
 * separately, so only the preview tile breaks.
 *
 * This mirrors dropzone's default handler but ignores a non-string dataUrl,
 * leaving the generic file placeholder in place. It deliberately does not
 * delegate to the built-in handler: the defaults are module-private in the
 * bundled build, so there is no supported way to reach it.
 */
export function thumbnail(file, dataUrl) {
    if (typeof dataUrl !== "string") return undefined;
    if (!file.previewElement) return undefined;

    file.previewElement.classList.remove("dz-file-preview");
    file.previewElement
        .querySelectorAll("[data-dz-thumbnail]")
        .forEach((thumbnailElement) => {
            thumbnailElement.alt = file.name;
            thumbnailElement.src = dataUrl;
        });

    // dropzone defers this so the class change lands after the src is applied
    return setTimeout(
        () => file.previewElement.classList.add("dz-image-preview"),
        1,
    );
}
