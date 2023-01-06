import '../vue/index.css';

export const parameters = {
  actions: { argTypesRegex: "^on[A-Z].*" },
  controls: {
    matchers: {
      color: /(background|color)$/i,
      date: /Date$/,
    },
  },
  themes: {
    clearable: false,
    default: 'Light mode',
    list: [
      { name: 'Light mode', class: 'light-mode', color: '#D3D3D3' },
      { name: 'Dark mode', class: 'dark-mode', color: '#696969' }
    ],
  },
}
