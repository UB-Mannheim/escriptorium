module.exports = {
    env: {
        node: true,
        commonjs: true,
        es6: true,
    },
    extends: [
        "eslint:recommended",
        "plugin:import/recommended",
        "plugin:vue/recommended",
        "plugin:storybook/recommended",
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
