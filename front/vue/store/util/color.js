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

/**
 * from baseline editor
 */
export function changeHue(rgb, degree) {
    // expects a string and returns an object
    function rgbToHSL(rgb) {
        // strip the leading # if it's there
        rgb = rgb.replace(/^\s*#|\s*$/g, "");

        // convert 3 char codes --> 6, e.g. `E0F` --> `EE00FF`
        if (rgb.length == 3) {
            rgb = rgb.replace(/(.)/g, "$1$1");
        }

        var r = parseInt(rgb.substr(0, 2), 16) / 255,
            g = parseInt(rgb.substr(2, 2), 16) / 255,
            b = parseInt(rgb.substr(4, 2), 16) / 255,
            cMax = Math.max(r, g, b),
            cMin = Math.min(r, g, b),
            delta = cMax - cMin,
            l = (cMax + cMin) / 2,
            h = 0,
            s = 0;

        if (delta == 0) {
            h = 0;
        } else if (cMax == r) {
            h = 60 * (((g - b) / delta) % 6);
        } else if (cMax == g) {
            h = 60 * ((b - r) / delta + 2);
        } else {
            h = 60 * ((r - g) / delta + 4);
        }

        if (delta == 0) {
            s = 0;
        } else {
            s = delta / (1 - Math.abs(2 * l - 1));
        }

        return {
            h: h,
            s: s,
            l: l,
        };
    }

    // expects an object and returns a string
    function hslToRGB(hsl) {
        var h = hsl.h,
            s = hsl.s,
            l = hsl.l,
            c = (1 - Math.abs(2 * l - 1)) * s,
            x = c * (1 - Math.abs(((h / 60) % 2) - 1)),
            m = l - c / 2,
            r,
            g,
            b;

        if (h < 60) {
            r = c;
            g = x;
            b = 0;
        } else if (h < 120) {
            r = x;
            g = c;
            b = 0;
        } else if (h < 180) {
            r = 0;
            g = c;
            b = x;
        } else if (h < 240) {
            r = 0;
            g = x;
            b = c;
        } else if (h < 300) {
            r = x;
            g = 0;
            b = c;
        } else {
            r = c;
            g = 0;
            b = x;
        }

        r = normalize_rgb_value(r, m);
        g = normalize_rgb_value(g, m);
        b = normalize_rgb_value(b, m);

        return rgbToHex(r, g, b);
    }

    function normalize_rgb_value(color, m) {
        color = Math.floor((color + m) * 255);
        if (color < 0) {
            color = 0;
        }
        return color;
    }

    function rgbToHex(r, g, b) {
        return (
            "#" +
            ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)
        );
    }

    var hsl = rgbToHSL(rgb);
    hsl.h += degree;
    if (hsl.h > 360) {
        hsl.h -= 360;
    } else if (hsl.h < 0) {
        hsl.h += 360;
    }
    return hslToRGB(hsl);
}
