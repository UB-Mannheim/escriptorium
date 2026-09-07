module.exports = {
    env: {
        browser: true,
        node: true,
        commonjs: true,
        es6: true,
    },
    globals: {
        "$": "readonly",
        "Cookies": "readonly",
        "Vue": "readonly",
        "paper": "readonly",
        "Path": "readonly",
        "Point": "readonly",
        "PointText": "readonly",
        "Size": "readonly",
        "Shape": "readonly",
        "Group": "readonly",
        "Rectangle": "readonly",
        "Tool": "readonly",
        "userProfile": "readonly",
        "DEBUG": "readonly",
        "Alert": "readonly",
        "Dropzone": "readonly",
        "ReconnectingWebSocket": "readonly",
        "UndoManager": "readonly",
        "Diff": "readonly",
        "math": "readonly",
        "moment": "readonly",
        "setupFormSet": "readonly",
        "addImageToLoader": "readonly",
        "enableVirtualKeyboard": "readonly",
    },
    extends: [
        "eslint:recommended",
        "plugin:import/recommended",
        "plugin:vue/recommended",
        "plugin:storybook/recommended",
    ],
    overrides: [
        {
            files: ["tests/**/*.spec.js"],
            env: { jest: true },
        },
        {
            // headless components: the empty <template /> is intentional,
            // the UI is provided by the base class / mixin
            files: [
                "vue/components/DiploLine.vue",
                "vue/components/SegLine.vue",
                "vue/components/SegRegion.vue",
            ],
            rules: {
                "vue/valid-template-root": "off",
            },
        },
    ],
    rules: {
        "arrow-parens": ["error", "always"],
        indent: [
            "error",
            4,
            {
                SwitchCase: 1,
            },
        ],
        quotes: ["warn", "double", { avoidEscape: true }],
        "vue/html-indent": ["warn", 4],
        "no-trailing-spaces": "error",
        "multiline-ternary": ["error", "always-multiline"],
        "max-len": ["warn", 100, { ignorePattern: 'd="([\\s\\S]*?)"' }],
        "no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
    },
};
