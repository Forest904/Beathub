const colors = require('tailwindcss/colors');

module.exports = {
  presets: [require('nativewind/preset')],
  content: [
    './src/**/*.{ts,tsx}',
    '../../packages/shared/src/**/*.{ts,tsx}',
  ],
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
};
