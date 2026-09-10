/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          950: '#08090d',
          900: '#0d0f15',
          800: '#141721',
          700: '#1d2130',
          600: '#2a2f42',
        },
        ember: {
          400: '#ff9a4d',
          500: '#ff7a1a',
          600: '#e8630a',
        },
      },
      fontFamily: {
        sans: [
          '"PingFang SC"',
          '"Microsoft YaHei"',
          '"Noto Sans SC"',
          'system-ui',
          'sans-serif',
        ],
      },
      boxShadow: {
        glow: '0 0 0 1px rgba(255,122,26,0.25), 0 18px 50px -20px rgba(255,122,26,0.35)',
      },
    },
  },
  plugins: [],
}

