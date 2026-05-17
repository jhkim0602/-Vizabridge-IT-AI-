import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          50: "#f6f7f9",
          100: "#eceef2",
          200: "#d6dae3",
          300: "#b0b7c7",
          400: "#828ca6",
          500: "#5f6a86",
          600: "#48526b",
          700: "#3a4258",
          800: "#272d3e",
          900: "#181c29",
        },
        brand: {
          50: "#eef5ff",
          100: "#d9e8ff",
          200: "#b6d2ff",
          300: "#85b2ff",
          400: "#5288ff",
          500: "#2f63f6",
          600: "#1f48dc",
          700: "#1c3ab1",
          800: "#1c328c",
          900: "#1c2e6f",
        },
      },
      fontFamily: {
        sans: [
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Pretendard",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
        mono: [
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Monaco",
          "Consolas",
          "monospace",
        ],
      },
    },
  },
  plugins: [],
};

export default config;
