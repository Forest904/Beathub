// tailwind.config.js
const colors = require('tailwindcss/colors');
const plugin = require('tailwindcss/plugin');
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand: colors.cyan,
        brandDark: colors.blue,
        brandSuccess: colors.emerald,
        brandError: colors.rose,
        brandWarning: colors.amber,
      },
    },
  },
  plugins: [],
  plugins: [
    plugin(function ({ addVariant }) {
      // Enable `light:` variant controlled by a `.light` class on the root
      addVariant('light', '.light &');
    }),
  ],
}
