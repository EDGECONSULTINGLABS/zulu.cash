/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'zcash-gold': '#F4B728',
        'cyber-purple': '#A855F7',
        'dark-bg': '#0a0a0f',
        'darker-bg': '#050508',
      },
    },
  },
  plugins: [],
}
