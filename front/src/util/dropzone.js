/**
 * Dropzone builds its preview thumbnails by loading the dropped file into an
 * <img>, and reuses one callback for both outcomes:
 *
 *     if (callback != null) { img.onerror = callback; }
 *     return img.src = file.dataURL;
 *
 * On success the callback receives a data URL; on failure it receives the DOM
 * error Event, which the default handler then assigns to img.src. That
 * stringifies to "[object Event]" and the browser requests it relative to the
 * current page, producing a 404 like
 *     GET /document/115/images/[object Event]
 *
 * It happens for every file the browser cannot decode -- always for TIFF, which
 * no browser renders in an <img>, and also for corrupt or CMYK images. The
 * upload itself is unaffected: Dropzone queues thumbnails and uploads
 * separately, so only the preview tile is broken.
 *
 * Wrap the default handler so a non-string is simply ignored, leaving the
 * generic file placeholder in place.
 */
export const guardThumbnail = (defaultThumbnail) =>
    function (file, dataUrl) {
        if (typeof dataUrl !== "string") return undefined;
        return defaultThumbnail.call(this, file, dataUrl);
    };
