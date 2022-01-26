const path = require('path');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const VueLoaderPlugin = require('vue-loader/lib/plugin')
const CompressionPlugin = require("compression-webpack-plugin");

module.exports = {
  entry: {
    vendor: './src/vendor.js',
    main: './src/main.js',
    editor: './src/editor/main.js',
    doclist: './src/documentlist/main.js',
    docstasks: './src/documentstasks/main.js'
  },

  output: {
    filename: '[name].js',
    path: path.resolve(__dirname, './dist/'),
    publicPath: '',
  },

  plugins: [
    new MiniCssExtractPlugin(),
    new VueLoaderPlugin(),
    new CompressionPlugin({
      test: /\.(js|css)$/,
    })
  ],

  module: {
    rules: [
      { test: /\.css$/,
        use: [MiniCssExtractPlugin.loader, 'css-loader'],
      },
      { test: /\.(png|jpe?g|gif|woff|woff2|eot|ttf|otf|svg)$/i,
        use: ['file-loader'],
      },
      { test: /\.vue$/,
        use: ['vue-loader'],
      }
    ]
  }, 

  resolve: {
    alias: {
      'vue$': 'vue/dist/vue'
    }
  }
};
