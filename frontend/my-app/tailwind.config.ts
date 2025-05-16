import type { Config } from 'tailwindcss';

const config: Config = {
    content: [
      './pages/**/*.{js,ts,jsx,tsx}',
      './components/**/*.{js,ts,jsx,tsx}',
      './app/**/*.{js,ts,jsx,tsx}', // if using Next.js 13+ app directory
    ],
    theme: {
      extend: {
        animation: {
          'fadeIn': 'fadeIn 0.3s ease-in-out',
        },
        keyframes: {
          fadeIn: {
            '0%': { opacity: '0', transform: 'translateY(-10px)' },
            '100%': { opacity: '1', transform: 'translateY(0)' },
          },
        },
      },
    },
  plugins: [
    require('@tailwindcss/typography'),
  ],
};

export default config;
  