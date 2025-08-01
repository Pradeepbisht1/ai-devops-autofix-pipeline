/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  darkMode: "class", // agar light mode nahi chahiye to isko hata bhi sakte ho ya default dark rakho
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "#22c55e", // green
          light: "#4ade80",
          dark: "#16a34a",
        },
        accent: {
          DEFAULT: "#0ea5e9", // blue
          light: "#38bdf8",
          dark: "#0284c7",
        },
        bg: "#0f172a", // deep navy
        card: "#1f2a3a", // slightly lighter
        border: "#2f3a5f",
        surface: "#1e233f",
        muted: "#6b7a9c",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      boxShadow: {
        glow: "0 10px 30px -5px rgba(56, 221, 248, 0.4)",
        card: "0 15px 40px -10px rgba(15, 23, 42, 0.6)",
      },
      borderRadius: {
        xl: "1rem",
      },
      transitionTimingFunction: {
        DEFAULT: "cubic-bezier(0.4, 0, 0.2, 1)",
      },
    },
  },
  plugins: [
    require("@tailwindcss/forms"),
    require("@tailwindcss/typography"),
  ],
};
