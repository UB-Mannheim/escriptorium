const path = require("path");
const MiniCssExtractPlugin = require("mini-css-extract-plugin");
const VueLoaderPlugin = require("vue-loader/lib/plugin");
const CompressionPlugin = require("compression-webpack-plugin");
const BundleTracker = require("webpack-bundle-tracker");
const { CleanWebpackPlugin } = require("clean-webpack-plugin");

module.exports = {
    entry: {
        vendor: "./src/vendor.js",
        main: "./src/main.js",
        editor: "./src/editor/main.js",
        doclist: "./src/documentlist/main.js",
        docstasks: "./src/documentstasks/main.js",
        documentDashboard: "./vue/exports/documentDashboard.js",
        globalNavigation: "./vue/exports/globalNavigation.js",
        projectDashboard: "./vue/exports/projectDashboard.js",
        projectsList: "./vue/exports/projectsList.js",
        imagesPage: "./vue/exports/imagesPage.js",
        ontologyOverviewPage: "./vue/exports/ontologyOverviewPage.js",
        modelTraining: "./vue/exports/modelTraining.js",
        downloads: "./vue/exports/downloads.js",
    },

    output: {
        filename: "bundles/[name].[contenthash:8].js",
        chunkFilename: "bundles/[name].[contenthash:8].chunk.js",
        path: path.resolve(__dirname, "./dist/"),
        publicPath: "/static/",
        clean: true,
    },

    plugins: [
        new CleanWebpackPlugin(),
        new MiniCssExtractPlugin({
            filename: "bundles/[name].[contenthash:8].css",
            chunkFilename: "bundles/[name].[contenthash:8].chunk.css",
        }),
        new VueLoaderPlugin(),
        new CompressionPlugin({
            test: /\.(js|css)$/,
        }),
        new BundleTracker({
            filename: path.resolve(__dirname, "./dist/webpack-stats.json"),
        }),
    ],

    module: {
        rules: [
            {
                test: /\.css$/,
                use: [MiniCssExtractPlugin.loader, "css-loader"],
            },
            {
                test: /\.(png|jpe?g|gif|woff|woff2|eot|ttf|otf|svg)$/i,
                use: ["file-loader"],
            },
            {
                test: /\.vue$/,
                use: [{ loader: "vue-loader", options: { prettify: false } }],
            },
        ],
    },

    resolve: {
        alias: {
            vue$: "vue/dist/vue",
        },
    },
};
