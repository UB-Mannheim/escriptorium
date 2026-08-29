const { merge } = require("webpack-merge");
const common = require("./webpack.common.js");

module.exports = merge(common, {
    mode: "production",
    resolve: {
        // use the production build of Vue (with template compiler) to avoid
        // shipping the development build and its console warnings
        alias: {
            vue$: "vue/dist/vue.min",
            "vue/dist/vue": "vue/dist/vue.min",
        },
    },
});
