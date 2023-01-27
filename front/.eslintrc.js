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
        quotes: ["warn", "double"],
        "vue/html-indent": ["warn", 4],
    },
};
