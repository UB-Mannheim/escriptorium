module.exports = {
  "stories": [
    "../src/**/*.stories.mdx",
    "../src/**/*.stories.@(js|jsx|ts|tsx)"
  ],
  "addons": [
    "@storybook/addon-links",
    {
      name: '@storybook/addon-essentials',
      options: {
        backgrounds: false,
      }
    },
    "@storybook/addon-interactions",
    "storybook-addon-themes",
    "@storybook/addon-a11y",
    "storybook-addon-mock",
  ],
  "framework": "@storybook/vue",
  "core": {
    "builder": "@storybook/builder-webpack5"
  }
}
