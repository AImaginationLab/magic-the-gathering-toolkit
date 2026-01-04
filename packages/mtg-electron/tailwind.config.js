/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/renderer/**/*.{html,tsx,ts}'],
  theme: {
    extend: {
      colors: {
        // MTG color palette
        mtg: {
          white: '#f8f6f0',
          blue: '#0e68ab',
          black: '#150b00',
          red: '#d3202a',
          green: '#00733e',
          gold: '#c9a227',
        },
      },
    },
  },
  plugins: [],
}
