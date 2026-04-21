/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        theme: {
          bg: '#f5f7fa',
          sidebar: '#ffffff',
          border: '#e1e4e8',
          text: '#1a1c21',
          dim: '#6a737d',
          accent: '#0969da',
          'accent-soft': 'rgba(9, 105, 218, 0.1)',
          tag: '#eff1f3',
        }
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Helvetica', 'Arial', 'sans-serif'],
        mono: ['JetBrains Mono', 'SFMono-Regular', 'Consolas', 'Liberation Mono', 'Menlo', 'monospace'],
      },
    },
  },
  plugins: [],
}