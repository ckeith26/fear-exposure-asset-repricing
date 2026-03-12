import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: "#1a1d27",
          dark: "#0f1117",
          light: "#ffffff",
          "light-alt": "#f8f9fa",
        },
        border: {
          DEFAULT: "#2a2d3a",
          light: "#e5e7eb",
        },
        accent: "#3b82f6",
        negative: "#ef4444",
        positive: "#22c55e",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
