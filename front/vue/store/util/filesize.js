// from Julian Hille's gist https://gist.github.com/julianhille/348ba88ba2b482f50086
export function filesizeformat(bytes, binary, precision) {
    /*
        Javascript filesizeformater.
        Inspired by jinja2 and some gists.

        @version 1.0.0
        @copyright 2014 Julian Hille
        @author Julian Hille
     */
    binary = typeof binary !== "undefined" ? binary : false;
    precision = typeof precision !== "undefined" ? precision : 2;
    var base = binary ? 1024 : 1000;
    var prefixes = [
        binary ? "KiB" : "kB",
        binary ? "MiB" : "MB",
        binary ? "GiB" : "GB",
        binary ? "TiB" : "TB",
        binary ? "PiB" : "PB",
        binary ? "EiB" : "EB",
        binary ? "ZiB" : "ZB",
        binary ? "YiB" : "YB",
    ];
    if (!isFinite(bytes)) {
        return "- Bytes";
    } else if (bytes == 1) {
        return "1 Byte";
    } else if (bytes < base) {
        return bytes + " Bytes";
    }
    var index = Math.floor(Math.log(bytes) / Math.log(base));
    return (
        parseFloat(
            (bytes / Math.pow(base, Math.floor(index))).toFixed(precision),
        ).toString() +
        " " +
        prefixes[index - 1]
    );
}
