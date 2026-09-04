/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#1c2a22",
        pine: "#2f5d4a",
        moss: "#4d7a62",
        paper: "#f4efe6",
        sand: "#e7dfd2",
        clay: "#c46a3a",
      },
      fontFamily: {
        sans: ["Pretendard", "Noto Sans KR", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
