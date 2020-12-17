const path = require('path');
const BundleTracker = require('webpack-bundle-tracker');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');

module.exports = {
  entry: {
    vendor: './src/vendor.js',
    main: './src/main.js',
    baseline_editor: './src/baseline_editor.js',
  },

  output: {
    filename: '[name].js',
    path: path.resolve(__dirname, './dist/'),
  },

  plugins: [
    new BundleTracker({filename: './dist/webpack-stats.json'}),
    new MiniCssExtractPlugin(),
  ],

  module: {
    rules: [
      { test: /\.css$/,
        use: [MiniCssExtractPlugin.loader, 'css-loader'],
      },
      { test: /\.(png|jpe?g|gif|woff|woff2|eot|ttf|otf|svg)$/i,
        use: ['file-loader'],
      }
    ]
  }
};
