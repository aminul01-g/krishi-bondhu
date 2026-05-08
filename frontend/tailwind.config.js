/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        primary: { DEFAULT: '#2D6A4F', light: '#40916C', dark: '#1B4332' },
        accent: { DEFAULT: '#D4A017', light: '#E9C46A' },
        danger: { DEFAULT: '#E63946', light: '#FFCCD5' },
        soil: '#8B6914',
        sky: '#90C2E7',
        surface: '#FFFFFF',
        bg: '#F7F5F0',
        border: '#E5E2DB',
        'text-primary': '#1A1A2E',
        'text-secondary': '#6B7280',
      },
      fontFamily: {
        sans: ["'Noto Sans Bengali'", "'Inter'", 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        card: '12px',
        btn: '12px',
        pill: '24px',
      },
      boxShadow: {
        card: '0 2px 8px rgba(0,0,0,0.08)',
        elevated: '0 8px 24px rgba(0,0,0,0.12)',
      },
    },
  },
  plugins: [],
};
