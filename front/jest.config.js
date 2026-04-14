module.exports = {
    testEnvironment: "jsdom",
    transform: {
        "^.+\\.vue$": "vue-jest",
        "^.+\\.js$": "babel-jest",
    },
    moduleNameMapper: {
        "\\.(css|less|scss|sass)$": "<rootDir>/tests/__mocks__/styleMock.js",
        "\\.(jpg|jpeg|png|gif|eot|otf|webp|svg|ttf|woff|woff2)$": "<rootDir>/tests/__mocks__/fileMock.js",
    },
    testMatch: ["**/tests/unit/**/*.spec.js"],
    moduleFileExtensions: ["js", "vue", "json"],
    setupFiles: ["<rootDir>/tests/setup.js"],
    collectCoverageFrom: [
        "src/**/*.js",
        "vue/**/*.vue",
        "!src/vendor.js",
        "!src/stories/**",
    ],
};
